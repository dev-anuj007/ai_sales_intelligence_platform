from __future__ import annotations

from pathlib import Path

import duckdb
import logfire

from services.storage.duckdb_connection import get_pool


def apply_schema(conn: duckdb.DuckDBPyConnection | None = None) -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema_sql = schema_path.read_text()

    if conn is None:
        conn = get_pool().get_connection()
        source = "pool"
    else:
        source = "provided"

    conn.execute(schema_sql)
    logfire.info("storage.schema_applied", source=source)
