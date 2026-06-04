# GitHub Copilot Instructions

## Purpose

This file is for repo-specific Copilot behavior, prompts, and guardrails.

For architecture and system design context, read these first instead of duplicating them here:
- `CLAUDE.md` for the system overview, workflow, and design patterns
- `LANGGRAPH_CONCEPTS.md` for LangGraph-specific implementation details

Project shorthand for Copilot:
- Production execution uses the Anthropic Claude API
- Copilot is used for code generation and review in the development workflow
- Preserve the existing LangGraph planner/executor/error-recovery/approval flow unless the user explicitly asks for an architecture change

---

## File Structure & Patterns

### Core Files (Don't Change Without Understanding)
```
src/orchestrator/orchestrator.py
├── SimpleCheckpointer        # SQLite state persistence
├── AgentState               # Pydantic state schema
├── AgentOrchestrator        # Main class with 5 nodes
└── _route_after_execution() # Conditional router logic

src/planner/planner.py
├── TaskPlanner              # LLM-based task decomposition
├── PLANNER_SYSTEM_PROMPT    # Instructions for Claude
└── plan()                   # Calls Claude API with tool_use

src/executor/executor.py
├── TaskExecutor             # Tool registry & execution
├── register_tool()          # Add new tool
└── execute()                # Run tool with error handling

src/aggregator/aggregator.py
├── ResultAggregator         # Compiles results into report
└── aggregate()              # Calls Claude API for polishing
```

### Tool Pattern
```python
# Location: src/tools/my_tool.py

class MyTool:
    @staticmethod
    def execute_action(parameter1: str, parameter2: int) -> dict:
        """
        Execute the action.
        
        Args:
            parameter1: What this does
            parameter2: What this does
        
        Returns:
            dict: {"result": ..., "status": "success/error"}
        """
        try:
            # Do work
            result = ...
            return {"result": result, "status": "success"}
        except Exception as e:
            return {"result": None, "status": "error", "error": str(e)}

# Register in main.py:
executor.register_tool("my_tool", MyTool.execute_action)
```

---

## How to Work With Copilot in This Project

### ✅ DO - Copilot Will Help With:

1. **Adding New Tools**
   - Copilot: "Add a tool that queries Slack"
   - It will: Create `slack_tool.py` following the pattern
   - You verify: Logic is correct, error handling works

2. **Creating New Nodes**
   - Copilot: "Add approval node for data access requests"
   - It will: Add node function, wiring, router logic
   - You verify: Routing is correct, state mutations are clean

3. **Adding Conditional Routes**
   - Copilot: "Route to approval_node if data_access_required"
   - It will: Update router function and conditional_edges
   - You verify: Logic handles all cases

4. **Implementing Self-Correction**
   - Copilot: "Add schema checking to error handler"
   - It will: Fetch schema, include in error context
   - You verify: Planner uses context correctly

5. **Code Cleanup & Refactoring**
   - Copilot: "Extract this repeated logic into a helper"
   - It will: Create function, update calls
   - You verify: Behavior unchanged, tests pass

6. **Adding Tests**
   - Copilot: "Write tests for executor node"
   - It will: Create test file with mocked state/tools
   - You verify: Tests cover edge cases

### ❌ DON'T - Don't Ask Copilot To:

1. **Redesign the state machine**
   - ❌ "Rewrite orchestrator to use async/await"
   - ✅ Instead: Discuss architecture changes in PR first

2. **Change core concepts**
   - ❌ "Replace Annotated[list, add] with a dict"
   - ✅ Instead: Understand why this pattern exists first

3. **Remove self-correction**
   - ❌ "Just fail on first error"
   - ✅ Instead: Modify error handling logic, keep self-correction

4. **Bypass human approval**
   - ❌ "Auto-send emails without approval"
   - ✅ Instead: Use approval node for all critical actions

---

## Common Copilot Requests & How To Phrase Them

### Request 1: Add Slack Tool
```
Copilot, I want to add Slack integration. Create:
1. src/tools/slack_tool.py with methods to read/send messages
2. Update main.py to register the tool
3. Add SLACK_BOT_TOKEN to .env

Follow the pattern in src/tools/sql_tool.py.
```

### Request 2: Add Jira Integration
```
Copilot, create a Jira tool that:
- Reads ticket details (summary, description, fields)
- Returns structured data (dict with ticket info)
- Handles API errors gracefully

Pattern: src/tools/jira_tool.py
Register in main.py with executor.register_tool("jira_read", JiraTool.get_ticket)
```

### Request 3: Create Dashboard Node
```
Copilot, add a new node called 'dashboard_generator':
1. Input: step_results from executor
2. Logic: If query results exist, generate Streamlit dashboard code
3. Output: dashboard_code string
4. Wire into graph before aggregator

Reference: _executor_node() for pattern
Use: python_exec tool to generate code
```

### Request 4: Self-Correction for Schema
```
Copilot, improve error_handler_node to:
1. Detect "no such table" errors
2. Call snowflake_metadata_tool.get_available_tables()
3. Suggest alternatives in error message
4. Include in state.errors for replanner context

Reference: error_handler_node at line 270
The planner should see available tables when replanning.
```

---

## Testing With Copilot

### Unit Tests
```
Copilot, write tests for executor.py:
1. Test successful tool execution
2. Test tool failure handling
3. Test step_index increment
4. Test step_results accumulation

Use: pytest fixtures with mocked tools
Keep tests in tests/test_executor.py
```

### Integration Tests
```
Copilot, write integration tests:
1. Mock Slack message → Jira ticket → Snowflake query flow
2. Verify state accumulation through all nodes
3. Test error recovery (plan fails → replan → succeeds)
4. Test approval gate blocking

Reference: tests/ directory
Use: pytest with fixture for AgentState
```

---

## Code Review Checklist (Use Copilot Chat)

After Copilot generates code, ask it to review:

```
Copilot, review this code for:
1. Does it follow the tool pattern?
2. Are state mutations clean (only changed fields)?
3. Does error handling include error messages?
4. Is it registering the tool in main.py?
5. Are there any edge cases missed?
```

---

## Development Workflow

### 1. Start Copilot Workspace
- Open: https://copilot.github.com
- Import: Your GitHub repo URL
- Wait: Copilot indexes the codebase

### 2. Describe What You Want
```
I want to add Slack integration to read data requests
from a #data-requests channel and auto-generate
Snowflake queries. The request should:
1. Be triggered by Slack message with Jira link
2. Read Jira ticket for requirements
3. Check Snowflake for available tables
4. Generate SQL query
5. Send result back to Slack with human approval
```

### 3. Let Copilot Generate
- It will create files (slack_tool.py, jira_tool.py, etc.)
- It will update orchestrator.py with new nodes
- It will update main.py with registrations

### 4. Review & Test
- Read generated code
- Ask Copilot: "Are there any issues?"
- Run locally: `python main.py` (uses real Claude API)
- Make adjustments if needed

### 5. Commit & Push
```bash
git add .
git commit -m "Add Slack + Jira integration for data requests"
git push origin feature/slack-jira-integration
```

---

## Key Concepts Copilot Should Know

### Annotated[list, add]
- Used for `step_results` and `errors`
- Means "append, never replace"
- Maintains audit trail throughout execution
- **Don't change this pattern**

### State Mutations
- Nodes return only changed fields
- LangGraph merges returned dict into state
- Example: `return {"current_step_index": 1}` increments, keeps everything else
- **Don't mutate state directly**

### Checkpointing
- SimpleCheckpointer saves state after each node
- Uses thread_id to identify execution
- Allows resuming interrupted workflows
- **Must be implemented for long-running tasks**

### Self-Correction Loop
- Error → error_handler fetches context → planner replans
- Max 3 replans, then gives up (prevents infinite loops)
- Schema context helps planner avoid same mistake
- **This is the core innovation**

---

## Environment Variables

```env
# Production (Claude)
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///agent_data.db
LOG_LEVEL=INFO

# Slack Integration (if adding)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Jira Integration (if adding)
JIRA_URL=https://jira.company.com
JIRA_API_TOKEN=...

# Snowflake Integration (if adding)
SNOWFLAKE_ACCOUNT=xy12345
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_WAREHOUSE=...
```

---

## Documentation References

When Copilot asks questions, direct it to:

1. **CLAUDE.md** - Architecture decisions & workflows
2. **LANGGRAPH_CONCEPTS.md** - Core LangGraph patterns
3. **LANGGRAPH_FLOW.md** - Visual diagrams
4. **README.md** - How to run the project

---

## Quick Start with Copilot

### Session 1: Understand the Codebase
```
Copilot: "Explain the 5-node architecture in this codebase"
→ It will describe planner, executor, error_handler, approval, aggregator

Copilot: "Show me how tools are registered and executed"
→ It will reference executor.py and tool patterns

Copilot: "How does self-correction work?"
→ It will explain error_handler + planner loop
```

### Session 2: Add a Feature
```
Copilot: "I need to add Slack integration. Generate slack_tool.py"
→ It will create the file following patterns

Copilot: "Wire this into the orchestrator as a new node"
→ It will update orchestrator.py

Copilot: "Review the changes for correctness"
→ It will validate against architecture
```

### Session 3: Test & Deploy
```
Copilot: "Write tests for the new Slack node"
→ It will create pytest tests

Copilot: "Run the full agent workflow with these new tools"
→ You run: python main.py (uses real Claude API)

Copilot: "Generate a commit message"
→ It will write clear message
```

---

## Tips for Best Results

1. **Be Specific**
   - ❌ "Add Slack" 
   - ✅ "Add Slack tool that reads messages with Jira links"

2. **Reference Patterns**
   - ❌ "Create a tool"
   - ✅ "Create a tool following the pattern in sql_tool.py"

3. **Show Examples**
   - Copy existing code patterns when asking for new features
   - Say "Follow this same structure"

4. **Ask for Reviews**
   - Always ask: "Review this for edge cases"
   - Always ask: "Does this follow our patterns?"
   - Always ask: "Any security issues?"

5. **Test Immediately**
   - Generate code
   - Run: `python main.py`
   - Verify with real Claude API (production engine)

---

## Getting Help

If Copilot generates code that doesn't work:

1. **Check the error message**
   - Share it with Copilot: "Fix this error"

2. **Verify state mutations**
   - Ask: "Are we mutating state correctly?"

3. **Check tool registration**
   - Ask: "Is this tool registered in main.py?"

4. **Test isolated**
   - Run `pytest tests/test_my_feature.py`
   - Ask Copilot: "Debug this test failure"

---

## Success Metrics

You're using the hybrid approach well when:

✅ Copilot generates 80% of new tool code  
✅ You review & test before committing  
✅ Claude API handles actual agent execution (production)  
✅ Self-correction loops work automatically  
✅ Code follows established patterns  
✅ All changes have audit trails  
✅ Human approval gates work correctly  

---

**Ready to start? Open GitHub Copilot Workspace and describe what you want to build!**
