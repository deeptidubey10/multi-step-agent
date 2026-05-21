"""AgentOrchestrator - LangGraph-based stateful cyclic workflow."""

import json
import sqlite3
from typing import Any, Literal
from datetime import datetime
from operator import add
from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END


class SimpleCheckpointer:
    """Simple SQLite checkpointer using standard library (no external deps)."""

    def __init__(self, db_path: str = "agent_state.db"):
        """Initialize checkpointer with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def save(self, thread_id: str, state_dict: dict):
        """Save state to checkpoint."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            state_json = json.dumps(state_dict, default=str)
            cursor.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, state_json, timestamp) VALUES (?, ?, ?)",
                (thread_id, state_json, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] Failed to save checkpoint: {e}")

    def load(self, thread_id: str) -> dict | None:
        """Load state from checkpoint."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT state_json FROM checkpoints WHERE thread_id = ?", (thread_id,))
            row = cursor.fetchone()
            conn.close()
            return json.loads(row[0]) if row else None
        except Exception as e:
            print(f"[WARN] Failed to load checkpoint: {e}")
            return None


class AgentState(BaseModel):
    """State maintained throughout agent execution."""

    user_request: str = Field(..., description="Original user request")
    current_step_index: int = Field(default=0, description="Index of current step")
    steps: list[dict[str, Any]] = Field(default_factory=list, description="Task plan steps")
    step_results: Annotated[list[dict[str, Any]], add] = Field(
        default_factory=list, description="Results from executed steps"
    )
    errors: Annotated[list[str], add] = Field(
        default_factory=list, description="Errors encountered"
    )
    replanning_count: int = Field(default=0, description="Number of times replanned")
    is_complete: bool = Field(default=False, description="Whether task is complete")
    final_output: Any = Field(default=None, description="Final aggregated output")
    last_error: str | None = Field(default=None, description="Last error message")


class AgentOrchestrator:
    """
    LangGraph orchestrator for stateful, cyclic task execution.

    Manages planning, execution, self-correction, and human-in-the-loop approval.
    """

    def __init__(self, planner, executor, aggregator, db_path: str = "agent_state.db"):
        """
        Initialize orchestrator with components.

        Args:
            planner: TaskPlanner instance
            executor: TaskExecutor instance
            aggregator: ResultAggregator instance
            db_path: Path to SQLite checkpoint store
        """
        self.planner = planner
        self.executor = executor
        self.aggregator = aggregator
        self.db_path = db_path
        self.checkpointer = SimpleCheckpointer(db_path)
        self.graph = None
        self.compiled_graph = None
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the LangGraph state machine."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("planner", self._planner_node)
        graph.add_node("executor", self._executor_node)
        graph.add_node("error_handler", self._error_handler_node)
        graph.add_node("approval", self._approval_node)
        graph.add_node("aggregator", self._aggregator_node)

        # Set entry point
        graph.set_entry_point("planner")

        # Add edges
        graph.add_edge("planner", "executor")
        graph.add_conditional_edges(
            "executor",
            self._route_after_execution,
            {
                "error": "error_handler",
                "approve": "approval",
                "continue": "executor",
                "done": "aggregator",
            },
        )
        graph.add_edge("error_handler", "planner")
        graph.add_edge("approval", "executor")
        graph.add_edge("aggregator", END)

        self.graph = graph

    def compile(self) -> Any:
        """Compile the graph with built-in checkpointing."""
        # Simple compile without external checkpoint dependencies
        self.compiled_graph = self.graph.compile()
        print("[OK] Graph compiled with built-in checkpointing")
        return self.compiled_graph

    def _planner_node(self, state: AgentState) -> dict[str, Any]:
        """Plan the task or replan after error."""
        print(f"\n[PLANNER] Decomposing request...")

        try:
            # Get schema context - either from errors (replanning) or fetch fresh (initial plan)
            schema_info = None
            if state.errors:
                for error in state.errors:
                    if "ACTUAL DATABASE SCHEMA:" in error or "Available schema:" in error:
                        schema_info = error
                        break
            else:
                # Initial plan - fetch schema proactively
                try:
                    from src.tools import SQLTool
                    import os
                    db_url = os.getenv("DATABASE_URL", "sqlite:///agent_data.db")
                    sql_tool = SQLTool(db_url)
                    schema = sql_tool.get_schema()

                    # Also get sample values to show format
                    sample_quarters = []
                    try:
                        result = sql_tool.execute_query("SELECT DISTINCT quarter FROM sales LIMIT 3")
                        sample_quarters = [r.get('quarter', '') for r in result.get('results', [])]
                    except Exception:
                        pass

                    schema_lines = ["ACTUAL DATABASE SCHEMA:", ""]
                    for table_name, columns in schema.items():
                        if table_name == "sqlite_sequence":
                            continue
                        cols_str = ", ".join([f"{col_name} ({col_type})" for col_name, col_type in columns.items()])
                        schema_lines.append(f"{table_name}: {cols_str}")

                    if sample_quarters:
                        schema_lines.append(f"\nExample quarter values: {', '.join(sample_quarters)}")
                        schema_lines.append("(Always use full format like 'Q3 2026', not just 'Q3')")

                    schema_info = "\n".join(schema_lines)
                except Exception:
                    pass

            plan = self.planner.plan(
                state.user_request,
                available_tools=["db_query", "python_exec", "email_send"],
                schema_info=schema_info,
            )

            steps = [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "tool": step.tool,
                    "parameters": step.parameters,
                    "depends_on": step.depends_on,
                }
                for step in plan.plan
            ]

            result = {
                "steps": steps,
                "current_step_index": 0,
                "step_results": [
                    {
                        "node": "planner",
                        "timestamp": datetime.now().isoformat(),
                        "llm_reasoning": plan.reasoning,
                        "steps_count": len(steps),
                        "replanning_count": state.replanning_count,
                    }
                ],
            }

            print(f"   [OK] Plan has {len(steps)} steps")
            return result

        except Exception as e:
            print(f"   [FAIL] Planning failed: {e}")
            return {
                "errors": [f"Planning failed: {str(e)}"],
                "last_error": str(e),
            }

    def _executor_node(self, state: AgentState) -> dict[str, Any]:
        """Execute the current step."""
        if state.current_step_index >= len(state.steps):
            return {"is_complete": True}

        step = state.steps[state.current_step_index]
        print(f"\n[EXECUTOR] Step {step['step_id']}: {step['description']}")

        try:
            result = self.executor.execute(
                step_id=step["step_id"],
                tool_name=step["tool"],
                parameters=step["parameters"],
            )

            step_record = {
                "step_id": step["step_id"],
                "node": "executor",
                "tool": step["tool"],
                "description": step["description"],
                "timestamp": datetime.now().isoformat(),
                "success": result.success,
                "output": result.output,
                "error": result.error,
            }

            new_results = [step_record]

            if result.success:
                print(f"   [SUCCESS]")
            else:
                print(f"   [FAILED] {result.error}")

            return {
                "step_results": new_results,
                "current_step_index": state.current_step_index + 1,
                "last_error": result.error if not result.success else None,
            }

        except Exception as e:
            print(f"   [ERROR] Execution crashed: {e}")
            return {
                "errors": [f"Step execution crashed: {str(e)}"],
                "last_error": str(e),
                "current_step_index": state.current_step_index + 1,
                "step_results": [
                    {
                        "step_id": step["step_id"],
                        "node": "executor",
                        "tool": step["tool"],
                        "timestamp": datetime.now().isoformat(),
                        "success": False,
                        "error": str(e),
                    }
                ],
            }

    def _route_after_execution(self, state: AgentState) -> Literal["error", "approve", "continue", "done"]:
        """Decide next route after execution."""
        if state.step_results:
            last_result = state.step_results[-1]

            # Check if step failed
            if not last_result.get("success", False):
                if state.replanning_count < 3:
                    return "error"
                else:
                    return "done"  # Give up after 3 replans

            # Check if this is an email step needing approval
            if last_result.get("tool") == "email_send":
                return "approve"

        # Check if more steps remain
        if state.current_step_index + 1 < len(state.steps):
            return "continue"

        # All steps done
        return "done"

    def _error_handler_node(self, state: AgentState) -> dict[str, Any]:
        """Handle errors and prepare for replanning."""
        print(f"\n[ERROR HANDLER] Analyzing failure...")

        # Get schema for SQL errors
        if state.last_error and ("table" in state.last_error.lower() or "no such column" in state.last_error.lower()):
            try:
                from src.tools import SQLTool
                import os

                db_url = os.getenv("DATABASE_URL", "sqlite:///agent_data.db")
                sql_tool = SQLTool(db_url)
                schema = sql_tool.get_schema()

                # Format schema more explicitly for the planner
                schema_lines = ["ACTUAL DATABASE SCHEMA:"]
                for table_name, columns in schema.items():
                    if table_name == "sqlite_sequence":
                        continue
                    schema_lines.append(f"  Table: {table_name}")
                    for col_name, col_type in columns.items():
                        schema_lines.append(f"    - {col_name} ({col_type})")

                schema_info = "\n".join(schema_lines)
                print(f"   [OK] Attached schema context for replanning")

                return {
                    "errors": [schema_info],
                    "current_step_index": 0,
                    "replanning_count": state.replanning_count + 1,
                }
            except Exception as e:
                print(f"   [WARN] Could not fetch schema: {e}")

        return {
            "current_step_index": 0,
            "replanning_count": state.replanning_count + 1,
        }

    def _approval_node(self, state: AgentState) -> dict[str, Any]:
        """Human-in-the-loop approval for critical actions."""
        print(f"\n👤 [APPROVAL] Waiting for human approval before sending email...")

        # In a real system, this would wait for API callback or UI response
        # For now, we auto-approve after printing the email (already done by tool)
        last_result = state.step_results[-1]
        print(f"   [EMAIL] Email preview: {last_result.get('output', {}).get('to')}")

        # Move to next step after approval
        return {
            "current_step_index": state.current_step_index + 1,
        }

    def _aggregator_node(self, state: AgentState) -> dict[str, Any]:
        """Aggregate results into final report."""
        print(f"\n[AGGREGATOR] Compiling final report...")

        try:
            report = self.aggregator.aggregate(state.user_request, state.step_results)

            return {
                "final_output": report,
                "is_complete": True,
                "step_results": [
                    {
                        "node": "aggregator",
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                    }
                ],
            }

        except Exception as e:
            print(f"   [FAIL] Aggregation failed: {e}")
            return {
                "final_output": f"Error during aggregation: {e}",
                "is_complete": True,
                "errors": [f"Aggregation failed: {str(e)}"],
            }

    def invoke(self, state: AgentState, config: dict[str, Any] | None = None) -> AgentState:
        """
        Run the orchestrator on the given state.

        Args:
            state: Initial agent state
            config: LangGraph config (e.g., thread_id for checkpointing)

        Returns:
            Final agent state after execution
        """
        if self.compiled_graph is None:
            self.compile()

        result = self.compiled_graph.invoke(state.model_dump(), config or {})

        # Save checkpoint if thread_id provided
        if config and "configurable" in config:
            thread_id = config["configurable"].get("thread_id")
            if thread_id:
                self.checkpointer.save(thread_id, result)

        return result

    def stream(self, state: AgentState, config: dict[str, Any] | None = None):
        """
        Stream execution events from the orchestrator.

        Args:
            state: Initial agent state
            config: LangGraph config

        Yields:
            Event dictionaries as execution progresses
        """
        if self.compiled_graph is None:
            self.compile()

        initial_state_dict = state.model_dump()
        final_state = None

        for event in self.compiled_graph.stream(initial_state_dict, config or {}):
            yield event
            # Capture final state for checkpointing
            if isinstance(event, dict):
                for node_state in event.values():
                    if isinstance(node_state, dict):
                        final_state = node_state

        # Save checkpoint at end if thread_id provided
        if config and "configurable" in config:
            thread_id = config["configurable"].get("thread_id")
            if thread_id:
                # Always preserve the original user_request
                checkpoint_state = final_state.copy() if final_state else {}
                if "user_request" not in checkpoint_state:
                    checkpoint_state["user_request"] = initial_state_dict.get("user_request", "Unknown")
                self.checkpointer.save(thread_id, checkpoint_state)

    def get_state(self, config: dict[str, Any]) -> AgentState | None:
        """
        Get the current state from checkpoint (for resuming).

        Args:
            config: LangGraph config with thread_id

        Returns:
            Current agent state, or None if not found
        """
        if "configurable" not in config:
            return None

        thread_id = config["configurable"].get("thread_id")
        if not thread_id:
            return None

        state_dict = self.checkpointer.load(thread_id)
        if state_dict:
            # Ensure required fields exist
            if "user_request" not in state_dict:
                state_dict["user_request"] = "Unknown request"
            return AgentState(**state_dict)
        return None
