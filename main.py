"""
Multi-Step Task Agent - Main Entry Point

Demonstrates a stateful, cyclic agent that dynamically plans tasks,
executes them with self-correction, and provides human-in-the-loop approval.
"""

import os
import logging
import uuid
from dotenv import load_dotenv

from src.planner import TaskPlanner
from src.executor import TaskExecutor
from src.orchestrator import AgentState, AgentOrchestrator
from src.aggregator import ResultAggregator
from src.tools import SQLTool, PythonTool, EmailTool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function - runs the multi-step agent."""
    logger.info("=" * 80)
    logger.info("Multi-Step Task Agent Starting")
    logger.info("=" * 80)

    # User request - the vague, complex command
    user_request = (
        "The revenue in the North region looks low for Q3. "
        "Find the top 3 failing products, draft a summary of why they are failing "
        "based on recent logs, and send it to the category manager."
    )

    logger.info(f"User request: {user_request}\n")

    # Initialize components
    planner = TaskPlanner(model="claude-3-5-haiku-20241022")
    executor = TaskExecutor()
    aggregator = ResultAggregator(model="claude-3-5-haiku-20241022")

    # Set up database
    db_url = os.getenv("DATABASE_URL", "sqlite:///agent_data.db")

    # Register tools with executor
    sql_tool = SQLTool(db_url)
    executor.register_tool("db_query", sql_tool.execute_query)
    executor.register_tool("python_exec", PythonTool.execute_with_output)
    executor.register_tool("email_send", EmailTool.send_email_static)

    logger.info("✓ Tools registered: db_query, python_exec, email_send\n")

    # Create orchestrator
    orchestrator = AgentOrchestrator(planner, executor, aggregator, db_path="agent_state.db")
    orchestrator.compile()

    # Create initial state
    initial_state = AgentState(user_request=user_request)

    # Configuration for LangGraph (thread_id for checkpointing)
    config = {"configurable": {"thread_id": f"run-{str(uuid.uuid4())[:8]}"}}

    logger.info("=" * 80)
    logger.info("Starting Execution Loop")
    logger.info("=" * 80 + "\n")

    try:
        # Stream execution with live events
        event_count = 0
        for event in orchestrator.stream(initial_state, config):
            event_count += 1

            # Events are dictionaries with node names as keys
            for node_name, node_state in event.items():
                if isinstance(node_state, dict):
                    # Node completed
                    pass

        logger.info("\n" + "=" * 80)
        logger.info("Execution Complete")
        logger.info("=" * 80)

        # Get final state from checkpoint
        final_state = orchestrator.get_state(config)

        if final_state.final_output:
            logger.info("\n📄 FINAL REPORT:")
            logger.info("-" * 80)
            print(final_state.final_output)
            logger.info("-" * 80)

        # Print audit trail
        logger.info("\n📊 AUDIT TRAIL:")
        logger.info("-" * 80)
        for i, result in enumerate(final_state.step_results, 1):
            if "step_id" in result:
                logger.info(
                    f"Step {result['step_id']}: {result.get('tool', 'unknown')} "
                    f"- {'✓' if result.get('success') else '✗'}"
                )
            elif "node" in result:
                logger.info(f"Node: {result['node']} at {result.get('timestamp')}")

        if final_state.is_complete:
            logger.info("\n✓ Agent completed successfully")
        else:
            logger.info("\n⚠ Agent did not complete (may have hit error limit)")

        if final_state.errors:
            logger.info(f"\n⚠ Errors encountered: {len(final_state.errors)}")
            for error in final_state.errors[:3]:
                logger.info(f"  - {error[:100]}...")

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
