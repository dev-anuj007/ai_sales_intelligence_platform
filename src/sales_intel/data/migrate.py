"""Database schema migration (idempotent).

Applies the DDL from schema.sql to ensure all tables exist.
Safe to run multiple times.
"""

from pathlib import Path

import duckdb
import logfire

from sales_intel.data.connection import get_connection_context


def apply_schema(conn: duckdb.DuckDBPyConnection | None = None) -> None:
    """Apply the database schema (CREATE TABLE IF NOT EXISTS).

    Args:
        conn: Optional DuckDB connection. If None, opens a temporary connection.

    Raises:
        FileNotFoundError: If schema.sql is not found.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema_sql = schema_path.read_text()

    if conn is None:
        with get_connection_context() as ctx:
            ctx.execute(schema_sql)
        logfire.info("database.schema_applied", source="temp_connection")
    else:
        conn.execute(schema_sql)
        logfire.info("database.schema_applied", source="provided_connection")
