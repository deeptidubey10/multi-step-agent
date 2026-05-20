# Installation & Setup Guide

## Prerequisites

- Python 3.10+
- pip (Python package manager)
- Internet connection (for API calls)
- Anthropic API key (get from https://console.anthropic.com/api_keys)

## Step-by-Step Installation

### 1. Clone/Navigate to Project
```bash
cd multi-step-agent
```

### 2. Create Virtual Environment (Recommended)

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**What gets installed:**
- `langgraph>=0.2.0` — Graph orchestration
- `langgraph-checkpoint-sqlite>=0.1.0` — Persistent state storage
- `langchain>=0.2.0` — Tool abstractions
- `langchain-anthropic>=0.1.0` — Claude integration
- `anthropic>=0.28.0` — Anthropic SDK
- `pydantic>=2.0.0` — Type validation
- `pandas>=2.0.0` — Data manipulation
- `numpy>=1.26.0` — Numerical computing
- `sqlalchemy>=2.0.0` — Database ORM
- `python-dotenv>=1.0.0` — Environment config
- `langsmith>=0.1.0` — LLM observability
- `python-pptx>=1.0.0` — PowerPoint generation
- `pytest>=7.0.0` — Testing framework

**Installation time:** ~2-5 minutes depending on internet speed

### 4. Configure Environment Variables

```bash
# Create .env file from template
cp .env.example .env

# Edit .env with your editor
# Add your ANTHROPIC_API_KEY
nano .env  # or use your favorite editor
```

**Minimum required in `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

**Optional:**
```
DATABASE_URL=sqlite:///agent_data.db
LOG_LEVEL=INFO
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=multi-step-agent
```

### 5. Seed Demo Database

```bash
python data/seed_data.py
```

**Output:**
```
✓ Database seeded at agent_data.db
  - sales table: 10 products × 4 regions × 4 quarters
  - product_logs table: 12-18 log entries for failing products
  - Q3 2026 North region: Products 6, 7, 8 are underperforming
```

### 6. Verify Installation

```bash
# Test 1: Check imports
python -c "import langgraph, langchain, anthropic; print('✓ All packages installed')"

# Test 2: Check API key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); key = os.getenv('ANTHROPIC_API_KEY'); print('✓ API key configured' if key else '✗ API key missing')"

# Test 3: Check database
python -c "import sqlite3; conn = sqlite3.connect('agent_data.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM sales'); print(f'✓ Database has {cursor.fetchone()[0]} sales records')"
```

---

## Getting Your API Key

1. Go to https://console.anthropic.com/api_keys
2. Sign up or log in to your Anthropic account
3. Click "Create Key" or "New Secret Key"
4. Copy the key (starts with `sk-ant-`)
5. Paste into `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
   ```

**Note:** Never commit `.env` to git — it contains secrets!

---

## Troubleshooting Installation

### Issue: `pip install` fails with permission error
```bash
# Use user install
pip install --user -r requirements.txt

# Or use sudo (not recommended)
sudo pip install -r requirements.txt
```

### Issue: `ModuleNotFoundError` after installation
```bash
# Verify you're in the virtual environment
which python  # Should show .venv/bin/python

# Reinstall packages
pip install -r requirements.txt --force-reinstall
```

### Issue: `langgraph-checkpoint-sqlite` not found
```bash
# Install directly
pip install langgraph-checkpoint-sqlite

# Or reinstall all
pip install -r requirements.txt --upgrade
```

### Issue: Python version too old
```bash
# Check version
python --version  # Should be 3.10+

# Install Python 3.10+ from python.org
```

---

## Running the Agent

Once installation is complete:

```bash
python main.py
```

**Expected output:**
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
[Report with findings...]
────────────────────────────────────────────────────────────────────────
```

---

## Optional: Install Additional Tools

### PowerPoint Generation
```bash
# For local PowerPoint creation
pip install python-pptx

# Or use MCP server (recommended for Claude Code)
pip install office-powerpoint-mcp-server
```

### LLM Observability
```bash
# For LangSmith (optional)
pip install langsmith

# For Langfuse (self-hosted alternative)
pip install langfuse
```

### Development Tools
```bash
# For testing
pip install pytest pytest-cov

# For linting
pip install ruff black

# For type checking
pip install mypy
```

---

## Docker Installation (Optional)

If you prefer containerized setup:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t multi-step-agent .
docker run -e ANTHROPIC_API_KEY=sk-ant-xxx multi-step-agent
```

---

## Verifying Everything Works

### Quick Test (1 minute)
```bash
python main.py
```

### Comprehensive Test (5 minutes)
```bash
# 1. Test database
python data/seed_data.py

# 2. Test planner
python -c "
from src.planner import TaskPlanner
planner = TaskPlanner()
plan = planner.plan('Find top products', ['db_query', 'python_exec'])
print('✓ Planner works:', len(plan.plan), 'steps')
"

# 3. Test executor
python -c "
from src.executor import TaskExecutor
from src.tools import SQLTool
executor = TaskExecutor()
sql_tool = SQLTool('sqlite:///agent_data.db')
executor.register_tool('db_query', sql_tool.execute_query_list)
result = executor.execute(1, 'db_query', {'query': 'SELECT COUNT(*) as count FROM sales'})
print('✓ Executor works:', result.output)
"

# 4. Run full agent
python main.py
```

---

## Next Steps After Installation

1. ✅ **Run the agent** — `python main.py`
2. 📖 **Read docs** — Start with `QUICK_START.md`
3. 🧪 **Test features** — Try modifying requests in `main.py`
4. 🎯 **Generate slides** — `python generate_slides.py`
5. 🔌 **Add MCP servers** — Configure Claude Code integrations

---

## Environment Setup Summary

| Component | Command | Status |
|-----------|---------|--------|
| Python 3.10+ | `python --version` | ✓ Required |
| Virtual env | `. .venv/bin/activate` | ✓ Recommended |
| Dependencies | `pip install -r requirements.txt` | ✓ Required |
| API key | In `.env` | ✓ Required |
| Database | `python data/seed_data.py` | ✓ Required |
| Optional tools | `pip install python-pptx` | ◯ Optional |

---

## Updating Dependencies

To update to the latest compatible versions:

```bash
# Update specific package
pip install --upgrade langgraph

# Update all
pip install --upgrade -r requirements.txt

# Check for outdated packages
pip list --outdated
```

---

## Uninstalling

To remove the project:

```bash
# Deactivate virtual environment
deactivate

# Delete the directory
rm -rf multi-step-agent

# Or just the virtual environment
rm -rf .venv
```

---

## Support

- **Installation issues** → See `TROUBLESHOOTING.md`
- **Quick start** → See `QUICK_START.md`
- **Detailed setup** → See `IMPLEMENTATION_SUMMARY.md`
- **API docs** → https://docs.anthropic.com/
- **LangGraph docs** → https://langchain-ai.github.io/langgraph/

All set! Run `python main.py` and you're ready to go. 🚀
