# Multi-Step Task Agent

A next-generation AI orchestrator that bridges high-level human reasoning with low-level technical execution. This system uses LLMs to dynamically plan and execute sequences of tasks to solve complex, multi-layered user requests.

## Overview

Unlike traditional static data pipelines (DAGs), this agent uses Claude to:
- **Decompose** complex requests into structured task plans
- **Execute** steps dynamically with error recovery
- **Aggregate** results into polished reports
- **Maintain state** throughout long-running operations

## Architecture

### Core Components

```
┌─────────────┐
│   Brain     │  LLM-based task decomposition
│  (Planner)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Orchestrator       │  LangGraph state machine
│ (Stateful Cyclic)   │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────┐
│    Executor          │  Tool wrapper management
│  (Error Recovery)    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   Hands (Tools)      │  SQL, Python, APIs
│   (Integrations)     │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│   Aggregator         │  Report generation
│   (Final Polishing)  │
└──────────────────────┘
```

## Project Structure

```
multi-step-agent/
├── src/
│   ├── __init__.py
│   ├── planner/              # Task decomposition
│   │   ├── __init__.py
│   │   └── planner.py
│   ├── executor/             # Step execution
│   │   ├── __init__.py
│   │   └── executor.py
│   ├── tools/                # Tool integrations
│   │   ├── __init__.py
│   │   ├── sql_tool.py
│   │   └── python_tool.py
│   ├── orchestrator/         # LangGraph workflow
│   │   ├── __init__.py
│   │   └── orchestrator.py
│   └── aggregator/           # Result compilation
│       ├── __init__.py
│       └── aggregator.py
├── tests/                    # Unit & integration tests
├── main.py                   # Entry point
├── requirements.txt
├── pytest.ini
├── CLAUDE.md                 # Full technical spec
└── README.md
```

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys
# ANTHROPIC_API_KEY=your_key_here
# DATABASE_URL=sqlite:///agent_state.db
```

### Running the Agent

```bash
python main.py
```

## Key Design Patterns

### 1. **Planner-Executor Pattern**
Separates "What to do" (Planner) from "How to do it" (Executor), allowing the LLM to focus on reasoning while tools handle execution.

### 2. **Stateful Reducer**
Uses `Annotated[List, operator.add]` to maintain a complete audit trail of all tool outputs throughout execution.

### 3. **Self-Correction Loop**
Validates tool outputs against expected schemas and automatically replans if execution fails.

## Technical Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Language | Python 3.10+ | Primary development |
| Orchestration | LangGraph | Stateful workflows |
| Framework | LangChain | Tool abstraction |
| LLM | Claude Haiku | Planning & reasoning |
| Data | Pandas/SQLAlchemy | Data manipulation |
| Validation | Pydantic | Schema enforcement |
| Persistence | SQLite | State checkpointing |
| Observability | LangSmith | Debugging & tracing |

## Development with GitHub Copilot

This project uses a **hybrid development approach**:
- **GitHub Copilot Workspace** - Fast code generation (https://copilot.github.com)
- **Claude API** - Production execution (Anthropic)

### Quick Start with Copilot
1. Open https://copilot.github.com
2. Import this repository
3. Ask: "Add a tool that does X"
4. Copilot generates code following established patterns
5. Test locally with `python main.py`
6. Commit when ready

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed instructions.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_planner.py
```

### Adding New Tools

1. Create a new tool wrapper in `src/tools/`
2. Register it with the TaskExecutor
3. Reference it by name in task plans

Example:
```python
from src.executor import TaskExecutor
from src.tools.my_tool import MyTool

executor = TaskExecutor()
executor.register_tool("my_tool", MyTool.execute)
```

## Workflow Example

```
User Request: "Analyze churn and email summary"
    ↓
Planner: Decomposes into 3 steps
    Step 1: Query churn data (db_query)
    Step 2: Calculate metrics (python_exec)
    Step 3: Send email (email_send)
    ↓
Executor: Runs each step with error recovery
    ↓
Aggregator: Compiles results into polished report
    ↓
User gets: Complete analysis + confirmation
```

## Documentation

### Essential Files
- **[CLAUDE.md](CLAUDE.md)** - Architecture decisions, design patterns, and technical context
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Instructions for GitHub Copilot Workspace
- **[LANGGRAPH_CONCEPTS.md](LANGGRAPH_CONCEPTS.md)** - Core LangGraph patterns with code references

### Additional Resources (in `docs/`)
- **[docs/GETTING_STARTED_HYBRID.md](docs/GETTING_STARTED_HYBRID.md)** - Hybrid development setup guide
- **[docs/HYBRID_DEVELOPMENT.md](docs/HYBRID_DEVELOPMENT.md)** - Complete development workflow
- **[docs/LANGGRAPH_FLOW.md](docs/LANGGRAPH_FLOW.md)** - Visual Mermaid diagrams of the workflow

## Contributing

1. Write tests for new features
2. Follow the component patterns established in [CLAUDE.md](CLAUDE.md)
3. Use GitHub Copilot Workspace for code generation ([see instructions](.github/copilot-instructions.md))
4. Test locally: `python main.py`
5. Ensure all tests pass before submitting

## License

[Add your license here]
