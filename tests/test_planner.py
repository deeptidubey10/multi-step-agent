"""Unit tests for the TaskPlanner."""

import pytest
from src.planner import TaskPlanner


class TestTaskPlanner:
    """Test cases for TaskPlanner."""

    @pytest.fixture
    def planner(self):
        """Fixture providing a TaskPlanner instance."""
        return TaskPlanner()

    def test_planner_initialization(self, planner):
        """Test that planner initializes correctly."""
        assert planner is not None
        assert planner.model is not None

    @pytest.mark.skip(reason="Requires API key - implement with mocked client")
    def test_plan_simple_request(self, planner):
        """Test planning a simple user request."""
        user_request = "Get the total sales for January"
        available_tools = ["db_query"]

        plan = planner.plan(user_request, available_tools)

        assert plan.user_request == user_request
        assert len(plan.plan) > 0
        assert all(step.tool in available_tools for step in plan.plan)

    @pytest.mark.skip(reason="Requires API key - implement with mocked client")
    def test_plan_complex_request(self, planner):
        """Test planning a complex multi-step request."""
        user_request = "Analyze churn patterns and send email summary"
        available_tools = ["db_query", "python_exec", "email_send"]

        plan = planner.plan(user_request, available_tools)

        assert len(plan.plan) >= 2
