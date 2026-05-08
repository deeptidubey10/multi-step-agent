"""TaskPlanner - Decomposes high-level user requests into structured task plans."""

import json
from typing import Any
from pydantic import BaseModel, Field
from anthropic import Anthropic


class TaskStep(BaseModel):
    """A single step in the execution plan."""

    step_id: int = Field(..., description="Unique step identifier")
    description: str = Field(..., description="Description of what this step does")
    tool: str = Field(..., description="Tool to use for this step (e.g., db_query, python_exec, email_send)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")
    depends_on: list[int] = Field(default_factory=list, description="List of step IDs this depends on")


class TaskPlan(BaseModel):
    """The complete task plan decomposed from user request."""

    user_request: str = Field(..., description="Original user request")
    plan: list[TaskStep] = Field(..., description="Ordered list of steps to execute")
    reasoning: str = Field(..., description="Reasoning behind the plan")


PLANNER_SYSTEM_PROMPT = """You are an expert task decomposition agent. Your job is to take vague, complex user requests and break them down into concrete, executable steps.

When given a user request, you must:
1. Understand the goal and constraints
2. Identify what data needs to be retrieved (SQL queries)
3. Identify what analysis needs to be done (Python code)
4. Identify what actions need to be taken (emails, reports)
5. Order the steps logically, respecting dependencies
6. Provide clear descriptions for each step

Available tools:
- db_query: Execute SQL SELECT queries and return results
  * IMPORTANT: Always include LIMIT clauses (typically LIMIT 1000)
  * Use WHERE clauses to filter data instead of returning all rows
  * For top-N queries, use ORDER BY + LIMIT
  * If you need ALL data, explicitly document why in the step description
- python_exec: Execute Python code for analysis, calculations, data transformation
- email_send: Send an email with subject, body, and recipient

Safety guidelines:
- Keep SQL queries focused (use WHERE to narrow scope)
- Use LIMIT 1000 by default unless specifically told otherwise
- For large datasets, use aggregation (COUNT, SUM, AVG) instead of fetching all rows
- If a query might be large, prefer TOP-N approaches with ORDER BY

Always output a structured plan with ordered steps. Each step should have:
- step_id: sequential integer starting from 1
- description: clear description of what the step does
- tool: the tool to use (db_query, python_exec, or email_send)
- parameters: dict of parameters needed for the tool (include LIMIT in SQL!)
- depends_on: list of step IDs this depends on (empty if no dependencies)"""


class TaskPlanner:
    """LLM-based task planner that decomposes requests into structured steps."""

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """Initialize the planner with an Anthropic client."""
        self.client = Anthropic()
        self.model = model

    def plan(self, user_request: str, available_tools: list[str]) -> TaskPlan:
        """
        Decompose a user request into a structured task plan.

        Uses Anthropic's tool_use feature for reliable JSON extraction.

        Args:
            user_request: The high-level user request
            available_tools: List of available tool names (for reference)

        Returns:
            TaskPlan: Structured plan with ordered steps
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": PLANNER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                {
                    "name": "create_task_plan",
                    "description": "Create a structured task plan to solve the user's request",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "user_request": {
                                "type": "string",
                                "description": "The original user request",
                            },
                            "plan": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_id": {"type": "integer"},
                                        "description": {"type": "string"},
                                        "tool": {"type": "string"},
                                        "parameters": {"type": "object"},
                                        "depends_on": {
                                            "type": "array",
                                            "items": {"type": "integer"},
                                        },
                                    },
                                    "required": [
                                        "step_id",
                                        "description",
                                        "tool",
                                        "parameters",
                                        "depends_on",
                                    ],
                                },
                                "description": "List of ordered steps",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Reasoning behind the plan",
                            },
                        },
                        "required": ["user_request", "plan", "reasoning"],
                    },
                }
            ],
            tool_choice={"type": "tool", "name": "create_task_plan"},
            messages=[
                {
                    "role": "user",
                    "content": f"""Create a task plan for the following request:

{user_request}

Available tools: {', '.join(available_tools)}

Break down the request into concrete steps, with dependencies clearly marked.""",
                }
            ],
        )

        # Extract tool input from response (tool_use is guaranteed to succeed)
        tool_result = message.content[0]
        if tool_result.type != "tool_use":
            raise ValueError(f"Expected tool_use, got {tool_result.type}")

        plan_data = tool_result.input
        return TaskPlan(**plan_data)
