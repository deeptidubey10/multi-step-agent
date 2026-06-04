# LangGraph Concepts - Concise Reference

## Core Concepts Used in This Project

### **StateGraph**
- Blueprint for the agent workflow; defines nodes and edges
- Created with a Pydantic state class: `graph = StateGraph(AgentState)`
- Compiled to executable graph: `compiled_graph = graph.compile()`
- *Used in:* [orchestrator.py:110](src/orchestrator/orchestrator.py#L110)

### **State (Pydantic BaseModel)**
- Holds all data flowing through the agent
- Immutable; nodes return dicts that merge into state (no mutation)
- *Fields in AgentState:*
  - `user_request`: Original prompt
  - `steps`: Task plan
  - `current_step_index`: Which step to execute
  - `step_results`: All execution outputs (accumulates)
  - `errors`: Error messages (accumulates)
  - `replanning_count`: How many retries
  - `is_complete`: Done?
  - `final_output`: Report
- *Used in:* [orchestrator.py:64-79](src/orchestrator/orchestrator.py#L64-L79)

### **Annotated[list, add]**
- Means "append to this field, don't replace it"
- `step_results: Annotated[list, add]` → each node appends its result
- Without it, each node would overwrite prior results
- *Used for:* `step_results` and `errors` (audit trail)
- *Used in:* [orchestrator.py:70-75](src/orchestrator/orchestrator.py#L70-L75)

### **Nodes**
- Functions that process state and return updates
- Signature: `def node(state: AgentState) -> dict[str, Any]`
- Returns only changed fields; LangGraph merges with existing state
- No side effects; pure functions (tools are called *from* nodes)
- *Nodes in project:*
  - `_planner_node`: Generates task plan
  - `_executor_node`: Runs current step, increments index
  - `_error_handler_node`: Fetches schema, increments retry counter
  - `_approval_node`: Human review gate for emails
  - `_aggregator_node`: Compiles final report
- *Used in:* [orchestrator.py:147-340](src/orchestrator/orchestrator.py#L147-L340)

### **Edges (Deterministic)**
- Hardcoded transition: A → B always
- `graph.add_edge("planner", "executor")` → planner always goes to executor
- *Used in:* [orchestrator.py:123, 134-135](src/orchestrator/orchestrator.py#L123)

### **Conditional Edges (Dynamic Routing)**
- Route based on state: `graph.add_conditional_edges("executor", router_fn, {"error": "error_handler", ...})`
- `router_fn` inspects state and returns which edge to take
- *Router logic in project:*
  - Failed & retries < 3 → error_handler
  - Failed & retries ≥ 3 → aggregator (give up)
  - Tool is email_send → approval (human gate)
  - More steps remain → executor (loop)
  - All done → aggregator (finish)
- *Used in:* [orchestrator.py:124-133](src/orchestrator/orchestrator.py#L124-L133)
- *Routing function:* [orchestrator.py:247-268](src/orchestrator/orchestrator.py#L247-L268)

### **Graph Compilation**
- `graph.compile()` converts StateGraph blueprint into executable Runnable
- Returns a synchronous (`.invoke()`) or streaming (`.stream()`) interface
- Optional: add checkpointer for persistent state
- *Used in:* [orchestrator.py:140-145](src/orchestrator/orchestrator.py#L140-L145)

### **Invoke vs Stream**
- **Invoke**: Run to completion, return final state
  - `result = graph.invoke(initial_state, config)`
- **Stream**: Emit events as each node completes
  - `for event in graph.stream(initial_state, config): ...`
- *Used in:* [main.py:78](main.py#L78) (stream mode for visibility)

### **Config (Thread ID)**
- `config = {"configurable": {"thread_id": "run-123"}}`
- Thread ID associates execution with a checkpoint (for resumable workflows)
- Passed to `.invoke()` or `.stream()`
- *Used in:* [main.py:69](main.py#L69)

### **Checkpointing**
- Persists state after each node completes
- Allows resuming interrupted workflows
- Custom checkpointer: `SimpleCheckpointer` (SQLite-backed)
- Saves/loads via `thread_id`
- *Checkpointer class:* [orchestrator.py:13-61](src/orchestrator/orchestrator.py#L13-L61)
- *Invoked during:* [orchestrator.py:390-398](src/orchestrator/orchestrator.py#L390-L398)

### **Reducer Pattern (operator.add)**
- `from operator import add`
- `Annotated[list, add]` means "merge lists by appending"
- Used for fields that accumulate without losing history
- *Used in:* [orchestrator.py:70, 73](src/orchestrator/orchestrator.py#L70-L73)

### **Tool Integration**
- Tools are NOT LangGraph nodes; they're called *from* nodes
- Executor node calls tools: `tool_output = tool(**parameters)`
- Each tool returns data → executor wraps in `step_result` dict → appends to state
- *Used in:* [executor.py:50](src/executor/executor.py#L50)

### **Self-Correction (Loop Back)**
- Error handler updates state with error details + schema context
- Resets `current_step_index = 0` (replan from scratch)
- Next iteration: planner sees error in state, generates new plan
- Repeats max 3 times before giving up
- *Used in:* [orchestrator.py:270-298](src/orchestrator/orchestrator.py#L270-L298)

### **Human-in-the-Loop (Interrupt)**
- Approval node pauses before critical actions (email)
- In real system: would call `interrupt()` and wait for user callback
- This project: auto-approves for demo; easily swappable for real approval
- *Used in:* [orchestrator.py:300-312](src/orchestrator/orchestrator.py#L300-L312)

### **State Mutations in Nodes**
- Nodes return `dict` with only *changed* fields
- LangGraph merges returned dict into current state
- Example: `return {"current_step_index": 1}` increments index, keeps everything else
- *Used in:* Every node returns selective updates, e.g. [executor.py:48-53](src/executor/executor.py#L48-L53)

### **Entry Point & Terminal Node**
- `graph.set_entry_point("planner")` → start here
- `graph.add_edge(..., END)` → terminal node (execution stops)
- *Used in:* [orchestrator.py:120, 136](src/orchestrator/orchestrator.py#L120-L136)

---

## Execution Flow (How It All Connects)

1. **Init**: `StateGraph(AgentState)` → `compile()` → ready
2. **Start**: `.stream(initial_state, config)` enters `planner` node
3. **Planner**: Generates `steps` list, returns `{"steps": [...], "current_step_index": 0}`
4. **Edge**: Deterministic edge → `executor` node
5. **Executor**: Runs `steps[0]`, appends result, increments index
6. **Router**: Conditional edge checks result → routes to `error_handler`, `approval`, or `executor` again
7. **Loop**: Self-correction cycle if needed
8. **End**: All steps done → `aggregator` → `END`
9. **Checkpoint**: State saved after each node (if checkpointer configured)

---

## Quick Reference: When to Use What

| Task | Use | Example |
|------|-----|---------|
| Transform state | **Node** | `planner_node()` generates plan |
| Run code/tools | **Call from node** | `tool(**params)` inside executor |
| Route conditionally | **Conditional edge** | Check if step failed → error_handler |
| Route always same way | **Regular edge** | planner → executor always |
| Accumulate history | **Annotated[list, add]** | `step_results` appends |
| Pause for human | **Approval node** | Email step waits for user |
| Retry on error | **Error handler + loop back** | Replan up to 3 times |
| Resume later | **Checkpointer + thread_id** | Save/load state by ID |

