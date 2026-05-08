# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create `.env` File
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
DATABASE_URL=sqlite:///agent_data.db
```

Get your key from: https://console.anthropic.com/

### 3. Seed Demo Data
```bash
python data/seed_data.py
```

Output:
```
✓ Database seeded at agent_data.db
  - sales table: 10 products × 4 regions × 4 quarters
  - product_logs table: 12-18 log entries for failing products
  - Q3 2026 North region: Products 6, 7, 8 are underperforming
```

### 4. Run the Agent
```bash
python main.py
```

Expected output:
```
================================================================================
Multi-Step Task Agent Starting
================================================================================

📋 [PLANNER] Decomposing request...
   ✓ Plan has 3 steps

⚙️  [EXECUTOR] Step 1: Find top 3 failing products in North region Q3 2026
   ✓ Success

⚙️  [EXECUTOR] Step 2: Analyze product logs to find failure reasons
   ✓ Success

⚙️  [EXECUTOR] Step 3: Draft summary and send to category manager
   ✓ Success

👤 [APPROVAL] Waiting for human approval before sending email...

📊 [AGGREGATOR] Compiling final report...

================================================================================
Execution Complete
================================================================================

📄 FINAL REPORT:
────────────────────────────────────────────────────────────────────────
[Markdown report with findings...]
────────────────────────────────────────────────────────────────────────

📊 AUDIT TRAIL:
────────────────────────────────────────────────────────────────────────
Step 1: db_query - ✓
Step 2: python_exec - ✓
Step 3: email_send - ✓
Node: planner at 2026-05-07T...
Node: aggregator at 2026-05-07T...

✓ Agent completed successfully
```

---

## What Just Happened?

The agent:
1. **Decomposed** your vague request into concrete steps (LLM planning)
2. **Queried** the database for North region Q3 2026 sales
3. **Analyzed** product logs to find failure reasons
4. **Drafted** an email summary
5. **Paused** for human approval before sending
6. **Compiled** results into a polished report

All while maintaining a **complete audit trail** of every decision.

---

## Understanding the Output

### Step Results
Each executed step is logged with:
- `step_id` — Unique step number
- `tool` — Tool used (db_query, python_exec, email_send)
- `success` — Whether it succeeded
- `output` — What the tool returned
- `timestamp` — When it ran

### Audit Trail
Complete record of:
- **Planner decisions** — How the LLM decomposed the request
- **Executor actions** — What each tool returned
- **Errors & recovery** — If a step failed, how it was corrected
- **Approval gates** — When humans had to approve

---

## Testing the Three Advanced Features

### 1. Test Dynamic Planning
**Modify the request in `main.py:18`:**
```python
user_request = "Find products with declining revenue trends in any region"
```
Run again — watch the LLM create a completely different plan!

### 2. Test Self-Correction
**Rename a column in `data/seed_data.py`:**
```python
cursor.execute("""CREATE TABLE sales (
    product_id INTEGER,
    product_name TEXT,
    region TEXT,
    quarter TEXT,
    revenue_amount REAL,  # ← Changed from "revenue"
    ...
)""")
```

Reseed & run:
```bash
python data/seed_data.py
python main.py
```

Watch the agent:
1. Execute SQL with old column name → Fail
2. Error handler inspects schema
3. Planner replans with correct column name
4. Retry succeeds ✓

### 3. Test Human-in-the-Loop
When `python main.py` pauses at email approval:
```
👤 [APPROVAL] Waiting for human approval before sending email...
```

**In production**, you'd send an HTTP POST:
```bash
# In another terminal, after seeing approval prompt:
curl -X POST http://localhost:8000/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "run-xyz123"}'
```

For now, the mock email is auto-approved after printing.

---

## Slide Deck Generation

After running the agent successfully:

```bash
python generate_slides.py
```

This creates a PowerPoint presentation with:
- Execution summary
- Steps executed
- Results & findings
- Audit trail visualization

*Note: Requires `python-pptx` library. Install with `pip install python-pptx`*

**Or use the MCP approach** (recommended):
```json
// In Claude Code settings.json:
"mcpServers": {
  "slides": {
    "command": "uvx",
    "args": ["office-powerpoint-mcp-server"]
  }
}
```

Then ask Claude Code:
> "Generate a PowerPoint slide deck from this agent execution audit trail. Include title, steps, results, and audit trail."

---

## File Reference

| File | Purpose |
|------|---------|
| `main.py` | Entry point — runs the agent |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for config (copy to `.env`) |
| `data/seed_data.py` | Creates sample SQLite database |
| `src/planner/planner.py` | Task decomposition (LLM) |
| `src/executor/executor.py` | Tool execution engine |
| `src/orchestrator/orchestrator.py` | LangGraph state machine |
| `src/tools/` | SQL, Python, Email wrappers |
| `generate_slides.py` | PowerPoint generation |
| `IMPLEMENTATION_SUMMARY.md` | Detailed what's been built |
| `ARCHITECTURE.md` | System design & patterns |

---

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'langgraph'`
**Fix:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: `ANTHROPIC_API_KEY not set`
**Fix:** Create `.env` with your key:
```bash
cp .env.example .env
# Edit .env, add ANTHROPIC_API_KEY
```

### Issue: `agent_data.db not found`
**Fix:** Seed the database:
```bash
python data/seed_data.py
```

### Issue: LLM response is slow
**Note:** First run is slower (no prompt cache). Subsequent runs use cached system prompt and are ~3x faster.

---

## Next Steps

1. ✅ **Run the agent** — Confirm it works end-to-end
2. 🎯 **Modify the request** — Test dynamic planning
3. 🔧 **Change the schema** — Test self-correction
4. 📊 **Generate slides** — Create PowerPoint presentation
5. 🔌 **Add MCP servers** — Extend with external tools
6. 📈 **Monitor with Langfuse** — Self-hosted LLM observability

---

## Learning Resources

- **CLAUDE.md** — Original specification & architecture
- **IMPLEMENTATION_SUMMARY.md** — What's been built
- **ARCHITECTURE.md** — Deep dive into system design
- **Code comments** — Each file has docstrings

---

## Getting Help

- **LangGraph docs:** https://langchain-ai.github.io/langgraph/
- **Anthropic API:** https://docs.anthropic.com/
- **Claude Code:** Type `/help` in Claude Code terminal
- **MCP Servers:** https://github.com/modelcontextprotocol/servers
