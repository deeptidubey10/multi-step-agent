# CLAUDE.md

**1. Executive Summary**
The Multi-Step Task Agent is a next-generation AI orchestrator designed to bridge the gap between high-level human reasoning and low-level technical execution. Unlike traditional "static" data pipelines (DAGs) which follow a fixed path, this agent uses a Large Language Model (LLM) to dynamically plan and execute a sequence of tasks to solve complex, multi-layered user requests.

For a Data Architect, this represents a transition from ETL (Extract, Transform, Load) to ADE (Autonomous Data Engineering).

**2. System Architecture**
The architecture is built on a Stateful Cyclic Graph pattern using LangGraph. This allows the system to maintain "memory" of previous steps and loop back to correct errors if a specific tool execution fails.

# Core Components:
The Brain (Planner): An LLM (Claude-3.5 or GPT-4) that receives the user request and decomposes it into a structured JSON plan.
The Nervous System (LangGraph Orchestrator): Manages the flow of data (the "State"), handles retries, and decides when the task is complete.
The Hands (Tool Wrappers): Python-based modules that allow the AI to interact with the real world (SQL Databases, Python Interpreters, APIs).
The Memory (State & Persistence): A SQLite-backed persistence layer that checkpoints the agent’s progress, allowing for long-running tasks and human-in-the-loop approvals.


**3. The Step-by-Step Workflow**
Step 1: Request & Decomposition (Planning Phase)
Action: The user provides a vague or complex prompt (e.g., "Analyze last month's churn and email the summary").
Logic: The Planner node analyzes the prompt against the available "Tool Library" and produces a Pydantic-validated list of steps.
Step 2: Orchestration (The State Machine)
Action: LangGraph initializes the AgentState.
Logic: It tracks the current_step_index. It ensures that Step 2 doesn't start until Step 1 provides the required output.
Step 3: Tool Execution (Action Phase)
Action: The Executor node identifies the tool required for the current step (e.g., db_query).
Logic: It invokes the tool wrapper. If the tool returns an error (e.g., "Table not found"), the error is added to the state, and the graph can route back to the Planner for a "Plan Revision."
Step 4: Human-in-the-Loop (Optional Gatekeeping)
Action: The graph hits a "Breakpoint" before a critical action (like sending an email).
Logic: Execution pauses. The state is saved. A human reviews the drafted email and provides a "Proceed" signal.
Step 5: Aggregation & Final Delivery
Action: Once all steps are finished, the Aggregator node compiles all intermediate results.
Logic: A final LLM pass converts raw data outputs into a polished report or response for the user.

**4. Technical Stack**
Category	    Technology	            Purpose
Language	    Python 3.10+	        Primary development language.
Orchestration	LangGraph	            Managing stateful, cyclic agent workflows.
Framework	    LangChain	            Tool abstraction, LLM interfacing, and prompt management.
LLMs	        Claude Haiku	        Reasoning, planning, and natural language generation.
Data Handling	Pandas/SQLAlchemy	    Data manipulation and DB connectivity.
Validation	    Pydantic	            Ensuring strict JSON schemas for planner outputs.
Persistence	    SQLite / Checkpointers	Saving agent state for "Resume" capabilities.
Observability	LangSmith	            Debugging and tracing LLM calls and tool latency.

**5. Key Design Patterns**
Planner-Executor Pattern: Separates the logic of "What to do" from "How to do it."
Stateful Reducer: Uses the Annotated[List, operator.add] pattern to ensure a full audit trail of tool outputs is maintained throughout the life of the task.
Self-Correction Loop: Allows the agent to "hallucinate" less by validating tool outputs against expected schemas and re-planning upon failure.

**6. Project Directory Structure**
multi-step-agent/
├── src/
│   ├── planner/        # LLM logic for decomposition
│   ├── executor/       # Logic for running specific tool steps
│   ├── tools/          # SQL, Python, and API wrappers
│   ├── orchestrator/   # LangGraph definition (Nodes/Edges)
│   └── aggregator/     # Final report generation
├── tests/              # Unit and Integration tests
├── .env                # API keys and secrets
└── main.py             # Entry point for the agent

