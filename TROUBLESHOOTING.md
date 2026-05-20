# Troubleshooting Guide

## Common Issues & Solutions

### 1. `ModuleNotFoundError: No module named 'langgraph'`

**Problem:** LangGraph is not installed

**Solution:**
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install langgraph langchain langchain-anthropic
```

---

### 2. `ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'`

**Problem:** SQLite checkpointing package is missing

**Solution:** Install the checkpoint SQLite package:
```bash
pip install langgraph-checkpoint-sqlite
```

Or reinstall all requirements:
```bash
pip install -r requirements.txt --upgrade
```

**Note:** If the package still isn't found, the agent will fall back to in-memory checkpointing (no persistence between runs, but still works).

---

### 3. `ANTHROPIC_API_KEY not set`

**Problem:** Missing API key in environment

**Solution:**
```bash
# Copy the template
cp .env.example .env

# Edit .env and add your key
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

Get your key from: https://console.anthropic.com/api_keys

---

### 4. `sqlite3.OperationalError: no such table`

**Problem:** Database not initialized

**Solution:**
```bash
# Seed the demo database
python data/seed_data.py
```

This creates `agent_data.db` with sample data.

---

### 5. `DATABASE_URL not configured`

**Problem:** Missing or invalid database URL

**Solution:** Set in `.env`:
```bash
# For local SQLite (default)
DATABASE_URL=sqlite:///agent_data.db

# For absolute path
DATABASE_URL=sqlite:////tmp/agent_data.db

# For in-memory (testing only)
DATABASE_URL=sqlite:///:memory:
```

---

### 6. Agent runs but produces no output

**Problem:** Execution is silent

**Cause:** Usually means an error in the LLM call or tool execution

**Debug:**
```bash
# Check logs
python main.py 2>&1 | tee debug.log

# Enable debug logging
LOG_LEVEL=DEBUG python main.py
```

**Common causes:**
- API key is invalid (check https://console.anthropic.com/account/keys)
- Network issue (API unreachable)
- Tool not registered properly
- SQL query fails silently

---

### 7. "Tool 'db_query' not registered"

**Problem:** Tools aren't registered with executor

**Check in `main.py`:**
```python
# Make sure this code runs:
executor.register_tool("db_query", sql_tool.execute_query)
executor.register_tool("python_exec", PythonTool.execute_with_output)
executor.register_tool("email_send", EmailTool.send_email_static)
```

If missing, the tools won't be available to the agent.

---

### 8. LLM returns malformed JSON

**Problem:** Claude's response doesn't parse correctly

**This shouldn't happen** because we use `tool_use` parameter (not text parsing).

**If it still occurs:**
- Check that `tool_choice={"type": "tool", "name": "create_task_plan"}` is set
- Verify `tools` parameter includes the correct schema
- Check that Anthropic SDK version is ≥0.28.0

---

### 9. SQL query hangs or times out

**Problem:** Query is too slow or returns too much data

**Solution:**
```python
# Add LIMIT to queries
sql_tool.execute_query("SELECT * FROM large_table LIMIT 1000")

# Or use WHERE to filter
sql_tool.execute_query(
    "SELECT * FROM sales WHERE region='North' AND quarter='Q3 2026'"
)

# Check token limits config
sql_tool = SQLTool(db_url, row_limit=1000, size_limit_mb=10)
```

---

### 10. Memory usage grows unbounded

**Problem:** Agent uses too much RAM

**Likely cause:** Accumulating step results in state

**Solution:**
```python
# Periodically trim old results if needed
# Or implement in aggregator node:
if len(state.step_results) > 100:
    state.step_results = state.step_results[-50:]  # Keep last 50
```

---

### 11. PowerPoint generation fails

**Problem:** `python generate_slides.py` errors

**Solution:** Install python-pptx
```bash
pip install python-pptx
```

**Or use MCP approach:**
```bash
# Install MCP server
pip install office-powerpoint-mcp-server

# Or use uvx (no install)
uvx office-powerpoint-mcp-server
```

---

### 12. `LangSmith_API_KEY` is optional but logging errors

**Problem:** Tracing errors when LangSmith key is missing

**Solution:** Either:
1. Add a valid LangSmith API key to `.env`
2. Or remove it — tracing is optional

```bash
# In .env, comment out if not using:
# LANGSMITH_API_KEY=...
# LANGSMITH_PROJECT=...
```

---

## Dependency Version Issues

If you hit version conflicts, try:

```bash
# Clear old packages
pip uninstall langgraph langchain anthropic -y

# Reinstall with explicit versions
pip install langgraph==0.2.6 langchain==0.2.11 anthropic==0.28.1
```

**Tested combinations:**
- `langgraph==0.2.6` + `langchain==0.2.11` + `anthropic==0.28.1` ✅
- `langgraph>=0.2.0` + `langchain>=0.2.0` + `anthropic>=0.28.0` ✅

---

## Performance Optimization

### Slow first run?
Normal — first run compiles the graph and may wait for LLM. Subsequent runs use cached prompts (3x faster).

### Slow SQL queries?
Add LIMIT and WHERE clauses:
```sql
-- Before (slow)
SELECT * FROM sales

-- After (fast)
SELECT * FROM sales 
WHERE region='North' AND quarter='Q3 2026'
LIMIT 100
```

### High API costs?
- Check token usage in logs
- Enable prompt caching (should be automatic with `cache_control`)
- Reduce `max_tokens` in API calls if desired
- Use Haiku model (cheaper) instead of Opus

---

## Debugging Checklist

- [ ] API key is set and valid
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Database exists: `python data/seed_data.py`
- [ ] .env file created from .env.example
- [ ] Tools registered in executor
- [ ] SQL queries have WHERE/LIMIT clauses
- [ ] Try running `python main.py` with `LOG_LEVEL=DEBUG`

---

## Getting Help

1. **Check logs:** Run with `LOG_LEVEL=DEBUG` for verbose output
2. **Test tools individually:**
   ```python
   from src.tools import SQLTool
   sql_tool = SQLTool("sqlite:///agent_data.db")
   result = sql_tool.execute_query("SELECT COUNT(*) FROM sales")
   print(result)
   ```

3. **Test planner:**
   ```python
   from src.planner import TaskPlanner
   planner = TaskPlanner()
   plan = planner.plan("Find failing products", ["db_query", "python_exec", "email_send"])
   print(plan)
   ```

4. **Reference documentation:**
   - `QUICK_START.md` — 5-minute setup
   - `IMPLEMENTATION_SUMMARY.md` — What's built
   - `ARCHITECTURE.md` — Technical details
   - `TOKEN_LIMITS.md` — Token safety

---

## Still Stuck?

1. Enable verbose logging:
   ```bash
   LOG_LEVEL=DEBUG python main.py 2>&1 | head -100
   ```

2. Verify each component:
   ```bash
   python -c "from langgraph.graph import StateGraph; print('✓ LangGraph OK')"
   python -c "from anthropic import Anthropic; print('✓ Anthropic OK')"
   python -c "import sqlalchemy; print('✓ SQLAlchemy OK')"
   ```

3. Check requirements match:
   ```bash
   pip show langgraph langchain anthropic
   ```

4. Try a minimal test:
   ```python
   import os
   from dotenv import load_dotenv
   load_dotenv()
   key = os.getenv('ANTHROPIC_API_KEY')
   print(f"API Key present: {'Yes' if key else 'No'}")
   ```
