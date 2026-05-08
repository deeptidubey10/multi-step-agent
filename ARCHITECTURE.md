# Architecture & System Design

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                                  │
│  "North region Q3 revenue is low — find failing products & email"   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   LangGraph     │
                    │   StateGraph    │  (src/orchestrator/orchestrator.py)
                    │                 │
         ┌──────────┴────────┬────────┴──────────┐
         │                  │                   │
    ┌────▼──┐          ┌────▼──┐          ┌────▼──┐
    │Planner │          │Executor│        │Aggregator
    └────┬──┘          └────┬──┘          └────┬──┘
         │                  │                   │
         │ LLM plan         │ Tool exec         │ LLM report
         │ (tool_use)       │ (registry)        │
         │                  │                   │
    ┌────▼──────────────────┴──────────────────▼───┐
    │           AgentState (Pydantic)               │
    │  ─────────────────────────────────────────   │
    │  • user_request                               │
    │  • steps[]           (from planner)           │
    │  • step_results[]    (accumulated)            │
    │  • errors[]          (accumulated)            │
    │  • replanning_count  (for self-correction)    │
    │  • final_output      (from aggregator)        │
    └──────────────────────┬───────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    │ Checkpoint  │  (agent_state.db)
                    │   Store     │
                    └─────────────┘
```

---

## Data Flow: Request to Execution

### 1. Planning Phase

```python
User Request
    ↓
planner.plan(request, available_tools)
    ↓
    └─→ Anthropic API (claude-3-5-haiku-20241022)
        • Prompt: "Decompose this request"
        • Tools: [create_task_plan tool definition]
        • Output: TaskPlan with steps
    ↓
state.steps = [
    {"step_id": 1, "tool": "db_query", "parameters": {...}},
    {"step_id": 2, "tool": "python_exec", "parameters": {...}},
    {"step_id": 3, "tool": "email_send", "parameters": {...}},
]
```

**Key insight:** Uses `tool_use` parameter instead of text JSON parsing.

### 2. Execution Phase

```python
For each step in state.steps:
    step = state.steps[current_step_index]
    
    result = executor.execute(
        tool_name=step["tool"],
        parameters=step["parameters"]
    )
    
    if result.success:
        state.step_results.append({
            "step_id": step["step_id"],
            "tool": step["tool"],
            "output": result.output,
            "success": True,
            "timestamp": now()
        })
        current_step_index += 1
    else:
        state.errors.append(result.error)
        → route to error_handler
```

### 3. Error Correction Cycle

```python
if step failed:
    # Error handler enriches state
    error_context = sql_tool.get_schema()  # Ask database
    state.errors.append(f"Available schema: {schema}")
    state.replanning_count += 1
    
    # Replan with error context
    planner.plan(state.user_request, tools)
    # LLM sees errors[] + schema → produces new plan
    
    # Reset and retry (up to 3 times)
    if replanning_count < 3:
        state.steps = new_plan.steps
        state.current_step_index = 0
        → back to executor
    else:
        → skip to aggregator
```

### 4. Human Approval (Email)

```python
if step.tool == "email_send":
    # Email tool executes (mock prints)
    state.step_results.append({...email details...})
    
    # Graph interrupts at approval_node
    → checkpointer saves state to SQLite
    → in production: await API /resume call
    
    # After human approves (POST /resume with thread_id):
    current_step_index += 1
    → continue to next step
```

### 5. Aggregation

```python
aggregator.aggregate(user_request, step_results)
    ↓
    └─→ Anthropic API (claude-3-5-haiku-20241022)
        • Inputs: all step_results[] + user_request
        • Task: "Compile these findings into a polished report"
        • Output: Markdown/text report
    ↓
state.final_output = report
state.is_complete = True
```

---

## Component Breakdown

### 1. Planner (`src/planner/planner.py`)

**Responsibility:** Decompose vague requests into concrete, executable steps

**Key method:** `plan(user_request: str, available_tools: list) → TaskPlan`

**Internals:**
```python
message = client.messages.create(
    model="claude-3-5-haiku-20241022",
    tools=[{
        "name": "create_task_plan",
        "input_schema": TaskPlan.model_json_schema()  # Pydantic schema
    }],
    tool_choice={"type": "tool", "name": "create_task_plan"},  # Force use
    system=[{
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}  # ← Prompt caching!
    }]
)
# Response is guaranteed tool_use, no parsing errors
plan_data = response.content[0].input  # Already a dict
```

**Why this approach:**
- No text parsing = no JSON markdown fences to strip
- Anthropic validates schema before returning = no malformed output
- Prompt caching on system prompt = 90% cost reduction on repeated calls

---

### 2. Executor (`src/executor/executor.py`)

**Responsibility:** Run tools and handle failures gracefully

**Key method:** `execute(step_id: int, tool_name: str, parameters: dict) → ExecutionResult`

**Tool Registry Pattern:**
```python
executor = TaskExecutor()
executor.register_tool("db_query", sql_tool.execute_query)
executor.register_tool("python_exec", PythonTool.execute_with_output)
executor.register_tool("email_send", EmailTool.send_email_static)

# Later:
result = executor.execute("db_query", {"sql": "SELECT ..."})
```

**Error handling:**
```python
try:
    output = self.tools[tool_name](**parameters)
    return ExecutionResult(success=True, output=output)
except Exception as e:
    return ExecutionResult(success=False, error=str(e))
    # No crash — orchestrator gets the error in state.errors[]
```

---

### 3. Tools (`src/tools/`)

#### SQLTool
```python
sql_tool = SQLTool("sqlite:///agent_data.db")

# Execute SELECT
results = sql_tool.execute_query("SELECT * FROM sales WHERE region=?", ["North"])

# Inspect schema (for self-correction)
schema = sql_tool.get_schema()
# → {"sales": {"product_id": "INTEGER", "revenue": "REAL", ...}, ...}
```

#### PythonTool
```python
result, stdout = PythonTool.execute_with_output(
    "import pandas as pd; df = pd.DataFrame([1,2,3]); print(df)",
    context={"data": [1,2,3]}
)
# → Returns computed value + captured stdout
```

#### EmailTool (Mock)
```python
response = EmailTool.send_email_static(
    to="manager@example.com",
    subject="Q3 North Revenue Analysis",
    body="Products 6,7,8 are failing due to..."
)
# → Prints to console (mock), returns {"sent": True, "mock": True}
```

---

### 4. Orchestrator (`src/orchestrator/orchestrator.py`)

**Responsibility:** Manage graph structure, node transitions, state persistence

**Node Functions:**

1. **planner_node** → Calls `planner.plan()`, updates `state.steps`
2. **executor_node** → Calls `executor.execute()` for current step, appends to `state.step_results`
3. **error_handler_node** → Enriches errors with schema context, increments `replanning_count`
4. **approval_node** → Pauses execution for human review (LangGraph `interrupt_before`)
5. **aggregator_node** → Calls `aggregator.aggregate()`, sets `state.final_output`

**Conditional Routing:**
```python
def route_after_execution(state):
    last_result = state.step_results[-1]
    
    if not last_result.get("success"):
        return "error"  # → error_handler → planner (replan)
    
    if last_result.get("tool") == "email_send":
        return "approve"  # → approval_node (pause)
    
    if state.current_step_index + 1 < len(state.steps):
        return "continue"  # → executor_node (next step)
    
    return "done"  # → aggregator_node
```

---

## State Management & Checkpointing

### AgentState (Pydantic Model)
```python
class AgentState(BaseModel):
    user_request: str                                      # Original request
    current_step_index: int = 0                           # Which step we're on
    steps: list[dict] = []                                # Task plan (from planner)
    step_results: Annotated[list, add] = []              # Accumulated results ← key!
    errors: Annotated[list, add] = []                    # Accumulated errors
    replanning_count: int = 0                             # Replan counter
    is_complete: bool = False                             # Done flag
    final_output: Any = None                              # Final report
```

**Key:** `Annotated[list, add]` uses `operator.add` for list concatenation.
- In LangGraph, when two states merge, lists are appended, not overwritten.
- Audit trail grows throughout execution.

### SQLite Checkpointing
```python
# Compile with checkpointer
checkpointer = SqliteSaver.from_conn_string("agent_state.db")
graph = graph.compile(checkpointer=checkpointer, interrupt_before=["approval"])

# Every state transition is saved
# Thread ID groups related operations
config = {"configurable": {"thread_id": "run-xyz"}}
final_state = graph.invoke(initial_state, config)

# Can resume from checkpoint:
state = graph.get_state(config)  # Retrieve latest saved state
```

---

## Execution Timeline Example

```
Time  Node            Event
────  ──────────────  ──────────────────────────────────────────
 0s   START
 1s   planner         LLM decomposes request → 3 steps
      state.steps = [{db_query}, {python_exec}, {email_send}]
      current_step_index = 0
 
 2s   executor        Execute step 0 (db_query for North Q3 sales)
      → sql_tool.execute_query("SELECT ... WHERE region='North' ...")
      → Returns 10 rows
      step_results[] += {step_id: 0, tool: "db_query", output: [...], success: true}
      current_step_index = 1
      
 3s   executor        Execute step 1 (python_exec for analysis)
      → PythonTool.execute_code("import pandas; top3 = df.nsmallest(3, 'revenue')")
      → Returns DataFrame + stdout
      step_results[] += {step_id: 1, tool: "python_exec", output: {...}, success: true}
      current_step_index = 2
      
 4s   executor        Execute step 2 (email_send)
      → EmailTool.send_email_static(to="...", subject="...", body="...")
      → Prints [EMAIL MOCK] to console
      step_results[] += {step_id: 2, tool: "email_send", output: {...}, success: true}
      
 5s   approval        ⏸ INTERRUPT — waiting for human approval
      state saved to agent_state.db (thread_id: run-xyz)
      
 6s   [HUMAN APPROVES via API /resume]
      
 7s   executor        Continue after approval
      current_step_index = 3 (no more steps)
      
 8s   aggregator      Compile all results into final report
      LLM reads state.step_results[] + user_request
      → Generates polished Markdown report
      state.final_output = "## Report: North Q3 Analysis..."
      state.is_complete = true
      
 9s   END             Done!
```

---

## Three Advanced Patterns

### Pattern 1: Dynamic Planning
```
Hardcoded (❌):
  Step 1: Query sales
  Step 2: Analyze
  Step 3: Send email
  
Dynamic (✅):
  User: "Find failing products and email them"
  LLM: [decides steps at runtime based on request]
  
Implementation: planner_node calls Anthropic with user_request
```

### Pattern 2: Self-Correction
```
Static pipeline (❌):
  [Step fails] → Error → Done
  
Cyclic (✅):
  [Step fails] → error_handler → get_schema() → planner (replan)
  → executor (retry) → [success or 3-retry limit]
  
Implementation: error_handler_node → conditional_edge back to planner_node
```

### Pattern 3: Human-in-the-Loop
```
Fully autonomous (❌):
  [Send email] → Email sent (no approval)
  
Gated (✅):
  [Execute email step] → Email previewed → ⏸ Interrupt
  → Checkpointed to SQLite → Await /resume → Continue
  
Implementation: LangGraph interrupt_before=["approval"]
                SQLite checkpointer persists state
```

---

## Cost Optimization

| Technique | Savings | How |
|-----------|---------|-----|
| **Prompt Caching** | 90% tokens | `cache_control: ephemeral` on system prompt |
| **Haiku model** | 10x cheaper | `claude-3-5-haiku-20241022` vs Opus |
| **Tool-use format** | Fewer retries | No parsing errors = no replanning |
| **Early termination** | Fewer steps | Replan limit = 3 max |

**Example cost:**
- Without caching: 10 steps × 5K tokens = 50K tokens × $0.80/1M = $0.04
- With caching: 1 cache write (3.75K) + 9 cache hits = 2.5K + 9 cache tokens = ~$0.01
- **4x savings with prompt caching**

---

## Slide Deck Generation (Next Phase)

Once agent execution completes:

```python
# Option 1: Python library (python-pptx)
python generate_slides.py --method pptx

# Option 2: MCP integration (recommended)
# Configure office-powerpoint-mcp-server in Claude Code
# Ask: "Generate slides from this audit trail..."
```

The script reads `agent_state.db` and generates:
1. **Title slide** - Execution summary
2. **Steps** - What the agent did
3. **Results** - Top 3 failing products
4. **Analysis** - Why they're failing (logs)
5. **Recommendation** - Send email to manager
6. **Audit trail** - Complete decision log

---

## Testing Strategy

| Test | Command | Expected Output |
|------|---------|---|
| **Demo run** | `python main.py` | Agent completes, prints report |
| **Self-correction** | Modify schema, run | Agent replans, succeeds |
| **Approval** | Run main.py | Agent pauses at email |
| **Audit trail** | Query agent_state.db | 5+ node entries |
| **Slide deck** | `python generate_slides.py` | agent_report.pptx created |

---

## Future Enhancements

1. **Parallel execution** - Run independent steps concurrently
2. **Real SMTP email** - Replace mock with smtplib
3. **LangSmith integration** - Monitor & debug agent traces
4. **Langfuse observability** - Self-hosted LLM observability
5. **Secure Python execution** - Sandbox code with subprocess
6. **Token flow limits** - Cap SQL result sizes
