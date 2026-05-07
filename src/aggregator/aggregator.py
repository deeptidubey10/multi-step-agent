"""ResultAggregator - Compiles intermediate results into final polished reports."""

from typing import Any
from anthropic import Anthropic


class ResultAggregator:
    """Aggregates task step results into a final formatted report."""

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """Initialize the aggregator with LLM client."""
        self.client = Anthropic()
        self.model = model

    def aggregate(self, user_request: str, step_results: list[dict[str, Any]]) -> str:
        """
        Compile step results into a polished final report.

        Args:
            user_request: The original user request
            step_results: Results from all executed steps

        Returns:
            Formatted final report as string
        """
        results_text = "\n".join(
            [
                f"Step {r.get('step_id', i)}: {r.get('output', 'No output')}"
                for i, r in enumerate(step_results)
            ]
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a data analyst. Compile the following intermediate results into a clear, polished final report.

Original request: {user_request}

Intermediate results:
{results_text}

Provide a well-formatted, professional report that answers the original request based on these results.""",
                }
            ],
        )

        return message.content[0].text

    def format_as_json(self, step_results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Format results as structured JSON.

        Args:
            step_results: Results from executed steps

        Returns:
            Structured JSON representation
        """
        return {
            "steps": step_results,
            "metadata": {
                "total_steps": len(step_results),
                "successful_steps": sum(1 for r in step_results if r.get("success", False)),
            },
        }

    def format_as_markdown(self, step_results: list[dict[str, Any]]) -> str:
        """
        Format results as markdown.

        Args:
            step_results: Results from executed steps

        Returns:
            Markdown formatted report
        """
        lines = ["# Execution Report\n"]

        for i, result in enumerate(step_results, 1):
            lines.append(f"## Step {i}: {result.get('description', 'No description')}\n")

            if result.get("success"):
                lines.append("**Status**: ✓ Success\n")
            else:
                lines.append("**Status**: ✗ Failed\n")

            if result.get("output"):
                lines.append(f"**Output**:\n```\n{result['output']}\n```\n")

            if result.get("error"):
                lines.append(f"**Error**: {result['error']}\n")

        return "\n".join(lines)
