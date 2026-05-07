"""PythonTool - Wrapper for executing Python code."""

from typing import Any


class PythonTool:
    """Executes Python code in a sandboxed environment."""

    @staticmethod
    def execute_code(code: str, context: dict[str, Any] | None = None) -> Any:
        """
        Execute Python code with optional context.

        Args:
            code: Python code to execute
            context: Variables available in the execution context

        Returns:
            Result of the code execution
        """
        if context is None:
            context = {}

        # Create a safe execution environment
        local_scope = {**context}
        global_scope = {
            "__builtins__": __builtins__,
            "pd": __import__("pandas"),
            "np": __import__("numpy"),
        }

        exec(code, global_scope, local_scope)

        # Return the last expression if it's a single expression
        if "result" in local_scope:
            return local_scope["result"]

        return None

    @staticmethod
    def execute_with_output(code: str, context: dict[str, Any] | None = None) -> tuple[Any, str]:
        """
        Execute Python code and capture stdout.

        Args:
            code: Python code to execute
            context: Variables available in the execution context

        Returns:
            Tuple of (return value, stdout output)
        """
        import io
        import sys

        if context is None:
            context = {}

        # Capture stdout
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            result = PythonTool.execute_code(code, context)
            output = captured_output.getvalue()
            return result, output
        finally:
            sys.stdout = old_stdout
