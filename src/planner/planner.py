"""TaskPlanner - Decomposes high-level user requests into structured task plans."""

from typing import Any
from pydantic import BaseModel, Field
from anthropic import Anthropic


class TaskStep(BaseModel):
    """A single step in the execution plan."""

    step_id: int = Field(..., description="Unique step identifier")
    description: str = Field(..., description="Description of what this step does")
    tool: str = Field(..., description="Tool to use for this step (e.g., db_query, python_exec)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")
    depends_on: list[int] = Field(default_factory=list, description="List of step IDs this depends on")


class TaskPlan(BaseModel):
    """The complete task plan decomposed from user request."""

    user_request: str = Field(..., description="Original user request")
    plan: list[TaskStep] = Field(..., description="Ordered list of steps")
    reasoning: str = Field(..., description="Reasoning behind the plan")


class TaskPlanner:
    """LLM-based task planner that decomposes requests into structured steps."""

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """Initialize the planner with an Anthropic client."""
        self.client = Anthropic()
        self.model = model

    def plan(self, user_request: str, available_tools: list[str]) -> TaskPlan:
        """
        Decompose a user request into a structured task plan.

        Args:
            user_request: The high-level user request
            available_tools: List of available tool names

        Returns:
            TaskPlan: Structured plan with ordered steps
        """
        tools_description = ", ".join(available_tools)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are an AI task planner. Decompose the following user request into a structured JSON plan.

Available tools: {tools_description}

User request: {user_request}

Respond with a valid JSON object matching this structure:
{{
  "user_request": "...",
  "plan": [
    {{
      "step_id": 1,
      "description": "...",
      "tool": "...",
      "parameters": {{}},
      "depends_on": []
    }}
  ],
  "reasoning": "..."
}}""",
                }
            ],
        )

        import json

        response_text = message.content[0].text
        plan_data = json.loads(response_text)
        return TaskPlan(**plan_data)
