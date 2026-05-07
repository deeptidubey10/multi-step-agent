"""SQLTool - Wrapper for database query execution."""

import pandas as pd
from sqlalchemy import create_engine, text
from typing import Any


class SQLTool:
    """Executes SQL queries against a database."""

    def __init__(self, database_url: str):
        """Initialize SQL tool with database connection."""
        self.engine = create_engine(database_url)

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL SELECT query

        Returns:
            List of result rows as dictionaries
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row._mapping) for row in result.fetchall()]

    def execute_mutation(self, query: str) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.

        Args:
            query: SQL mutation query

        Returns:
            Number of affected rows
        """
        with self.engine.begin() as conn:
            result = conn.execute(text(query))
            return result.rowcount

    def get_dataframe(self, query: str) -> pd.DataFrame:
        """
        Execute a query and return results as DataFrame.

        Args:
            query: SQL SELECT query

        Returns:
            Pandas DataFrame with results
        """
        return pd.read_sql(query, self.engine)
