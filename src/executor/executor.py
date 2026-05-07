"""TaskExecutor - Executes individual task steps using tool wrappers."""

from typing import Any
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Result of executing a task step."""

    step_id: int = Field(..., description="ID of the executed step")
    success: bool = Field(..., description="Whether execution succeeded")
    output: Any = Field(default=None, description="Tool output data")
    error: str | None = Field(default=None, description="Error message if failed")


class TaskExecutor:
    """Executes task steps using registered tool wrappers."""

    def __init__(self):
        """Initialize the executor with tool registry."""
        self.tools = {}

    def register_tool(self, name: str, tool_fn) -> None:
        """Register a tool for use in execution."""
        self.tools[name] = tool_fn

    def execute(
        self, step_id: int, tool_name: str, parameters: dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute a single task step.

        Args:
            step_id: The step ID being executed
            tool_name: Name of the tool to use
            parameters: Parameters to pass to the tool

        Returns:
            ExecutionResult: Result of the tool execution
        """
        if tool_name not in self.tools:
            return ExecutionResult(
                step_id=step_id,
                success=False,
                error=f"Tool '{tool_name}' not registered",
            )

        try:
            tool = self.tools[tool_name]
            output = tool(**parameters)
            return ExecutionResult(step_id=step_id, success=True, output=output)
        except Exception as e:
            return ExecutionResult(step_id=step_id, success=False, error=str(e))
