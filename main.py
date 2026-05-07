"""
Multi-Step Task Agent - Main Entry Point

This is the entry point for the autonomous task execution agent.
"""

import os
import logging
from dotenv import load_dotenv
from src.planner import TaskPlanner
from src.executor import TaskExecutor
from src.orchestrator import AgentState
from src.aggregator import ResultAggregator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    logger.info("Starting Multi-Step Task Agent")

    # Example user request
    user_request = "Analyze the sales data for the past month and provide a summary"

    # Available tools
    available_tools = ["db_query", "python_exec", "email_send"]

    # Initialize components
    planner = TaskPlanner()
    executor = TaskExecutor()
    aggregator = ResultAggregator()

    try:
        # Step 1: Plan the task
        logger.info(f"Planning task: {user_request}")
        plan = planner.plan(user_request, available_tools)
        logger.info(f"Generated plan with {len(plan.plan)} steps")

        # Step 2: Execute the plan
        logger.info("Executing plan")
        results = []
        for step in plan.plan:
            result = executor.execute(step.step_id, step.tool, step.parameters)
            results.append(
                {
                    "step_id": result.step_id,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
            )
            if not result.success:
                logger.warning(f"Step {step.step_id} failed: {result.error}")

        # Step 3: Aggregate results
        logger.info("Aggregating results")
        final_report = aggregator.aggregate(user_request, results)
        logger.info("Task complete")

        print("\n" + "=" * 80)
        print("FINAL REPORT")
        print("=" * 80)
        print(final_report)

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
