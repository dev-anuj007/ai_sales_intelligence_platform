from __future__ import annotations

from pathlib import Path

import logfire

from config import settings


def apply_schema() -> None:
    """Apply schema based on configured database type."""
    if settings.db_type == "postgres":
        _apply_postgres_schema()
    else:
        _apply_duckdb_schema()


def _apply_duckdb_schema() -> None:
    """Apply DuckDB schema."""
    import duckdb

    from services.storage.duckdb_connection import get_pool

    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema_sql = schema_path.read_text()
    conn = get_pool().get_connection()
    conn.execute(schema_sql)
    logfire.info("storage.duckdb_schema_applied")


def _apply_postgres_schema() -> None:
    """Apply PostgreSQL schema using SQLModel."""
    from services.storage.postgres_connection import get_pool

    pool = get_pool()
    pool.create_all_tables()
    logfire.info("storage.postgres_schema_applied")
