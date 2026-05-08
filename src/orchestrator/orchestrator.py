"""AgentOrchestrator - LangGraph-based stateful cyclic workflow."""

from typing import Any, Literal
from datetime import datetime
from operator import add
from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver


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
        """Compile the graph with SQLite checkpointing."""
        checkpointer = SqliteSaver.from_conn_string(self.db_path)
        self.compiled_graph = self.graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["approval"],  # Pause before human approval nodes
        )
        return self.compiled_graph

    def _planner_node(self, state: AgentState) -> dict[str, Any]:
        """Plan the task or replan after error."""
        print(f"\n📋 [PLANNER] Decomposing request...")

        try:
            plan = self.planner.plan(
                state.user_request,
                available_tools=["db_query", "python_exec", "email_send"],
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

            print(f"   ✓ Plan has {len(steps)} steps")
            return result

        except Exception as e:
            print(f"   ✗ Planning failed: {e}")
            return {
                "errors": [f"Planning failed: {str(e)}"],
                "last_error": str(e),
            }

    def _executor_node(self, state: AgentState) -> dict[str, Any]:
        """Execute the current step."""
        if state.current_step_index >= len(state.steps):
            return {"is_complete": True}

        step = state.steps[state.current_step_index]
        print(f"\n⚙️  [EXECUTOR] Step {step['step_id']}: {step['description']}")

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
                print(f"   ✓ Success")
            else:
                print(f"   ✗ Failed: {result.error}")

            return {
                "step_results": new_results,
                "last_error": result.error if not result.success else None,
            }

        except Exception as e:
            print(f"   ✗ Execution crashed: {e}")
            return {
                "errors": [f"Step execution crashed: {str(e)}"],
                "last_error": str(e),
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
        print(f"\n🔧 [ERROR HANDLER] Analyzing failure...")

        # Get schema for SQL errors
        if state.last_error and "table" in state.last_error.lower():
            try:
                from src.tools import SQLTool
                import os

                db_url = os.getenv("DATABASE_URL", "sqlite:///agent_data.db")
                sql_tool = SQLTool(db_url)
                schema = sql_tool.get_schema()

                schema_info = f"Available schema: {schema}"
                print(f"   ✓ Attached schema context for replanning")

                return {
                    "errors": [schema_info],
                    "current_step_index": 0,
                    "replanning_count": state.replanning_count + 1,
                }
            except Exception as e:
                print(f"   ⚠ Could not fetch schema: {e}")

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
        print(f"   📧 Email preview: {last_result.get('output', {}).get('to')}")

        # Move to next step after approval
        return {
            "current_step_index": state.current_step_index + 1,
        }

    def _aggregator_node(self, state: AgentState) -> dict[str, Any]:
        """Aggregate results into final report."""
        print(f"\n📊 [AGGREGATOR] Compiling final report...")

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
            print(f"   ✗ Aggregation failed: {e}")
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

        return self.compiled_graph.invoke(state.model_dump(), config or {})

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

        for event in self.compiled_graph.stream(state.model_dump(), config or {}):
            yield event

    def get_state(self, config: dict[str, Any]) -> AgentState:
        """
        Get the current state from checkpoint (for resuming).

        Args:
            config: LangGraph config with thread_id

        Returns:
            Current agent state
        """
        if self.compiled_graph is None:
            self.compile()

        state_dict = self.compiled_graph.get_state(config).values
        return AgentState(**state_dict)
