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

## Development

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

## Contributing

1. Write tests for new features
2. Follow the component patterns established
3. Update CLAUDE.md if architecture changes
4. Ensure all tests pass before submitting

## License

[Add your license here]
