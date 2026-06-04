"""SQLTool - Wrapper for database query execution with token/size limits."""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from typing import Any


class SQLTool:
    """Executes SQL queries against a database with safety limits."""

    # Default limits to prevent context overflow
    DEFAULT_ROW_LIMIT = 1000
    DEFAULT_SIZE_LIMIT_MB = 10

    def __init__(self, database_url: str, row_limit: int = DEFAULT_ROW_LIMIT, size_limit_mb: int = DEFAULT_SIZE_LIMIT_MB):
        """
        Initialize SQL tool with database connection and safety limits.

        Args:
            database_url: SQLAlchemy connection URL
            row_limit: Maximum rows per query (default 1000)
            size_limit_mb: Maximum result size in MB (default 10)
        """
        # Handle relative SQLite paths - convert to absolute
        if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:////"):
            db_path = database_url.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                # Convert relative path to absolute
                abs_path = os.path.abspath(db_path)
                database_url = f"sqlite:///{abs_path}"

        self.engine = create_engine(database_url)
        self.row_limit = row_limit
        self.size_limit_mb = size_limit_mb

    def execute_query(self, query: str, skip_limit: bool = False) -> dict[str, Any]:
        """
        Execute a SELECT query with automatic row limiting to prevent overflow.

        Args:
            query: SQL SELECT query
            skip_limit: If True, execute query without row limit (use carefully!)

        Returns:
            Dict with results, metadata, and warnings (if any)
        """
        # Add LIMIT clause if not already present and skip_limit=False
        if not skip_limit and "LIMIT" not in query.upper():
            limited_query = f"{query.rstrip(';')} LIMIT {self.row_limit}"
        else:
            limited_query = query

        with self.engine.connect() as conn:
            result = conn.execute(text(limited_query))
            rows = [dict(row._mapping) for row in result.fetchall()]

        # Estimate size (rough: ~500 bytes per row for typical data)
        estimated_size_mb = (len(rows) * 500) / (1024 * 1024)
        is_oversized = estimated_size_mb > self.size_limit_mb

        response = {
            "results": rows,
            "row_count": len(rows),
            "estimated_size_mb": round(estimated_size_mb, 2),
            "warnings": [],
        }

        # Add warnings for large results
        if len(rows) >= self.row_limit:
            response["warnings"].append(
                f"Query returned {self.row_limit}+ rows (truncated). "
                f"Results may be incomplete. Use skip_limit=True to override."
            )

        if is_oversized:
            response["warnings"].append(
                f"Result size ~{estimated_size_mb}MB exceeds safe limit ({self.size_limit_mb}MB). "
                f"Consider adding WHERE/ORDER BY to reduce data."
            )

        return response

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

    def execute_query_list(self, query: str) -> list[dict[str, Any]]:
        """
        Legacy method: Execute query and return just the results list.

        For new code, use execute_query() which returns metadata.

        Args:
            query: SQL SELECT query

        Returns:
            List of result rows as dictionaries
        """
        response = self.execute_query(query, skip_limit=False)
        return response["results"]

    def get_dataframe(self, query: str) -> pd.DataFrame:
        """
        Execute a query and return results as DataFrame.

        Args:
            query: SQL SELECT query

        Returns:
            Pandas DataFrame with results
        """
        return pd.read_sql(query, self.engine)

    def get_schema(self) -> dict[str, dict[str, str]]:
        """
        Retrieve database schema (table and column information).

        Used for self-correction when queries fail due to schema mismatches.

        Returns:
            Dict mapping table names to their columns and types
        """
        with self.engine.connect() as conn:
            # For SQLite, use sqlite_master
            tables_result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in tables_result.fetchall()]

            schema = {}
            for table in tables:
                columns_result = conn.execute(text(f"PRAGMA table_info({table})"))
                columns = {
                    row[1]: row[2]  # column name: type
                    for row in columns_result.fetchall()
                }
                schema[table] = columns

            return schema
