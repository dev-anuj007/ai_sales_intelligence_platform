"""DuckDB connection management.

Provides thread-safe access to a single shared DuckDB connection.
Designed for the FastAPI lifespan context; should not be opened concurrently
with CLI tools (single-writer limitation of DuckDB).
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import duckdb

from sales_intel.config import settings

# Global connection instance (opened once at app startup)
_connection: duckdb.DuckDBPyConnection | None = None


def get_shared_connection() -> duckdb.DuckDBPyConnection:
    """Get the shared DuckDB connection (assumes it's already opened).

    Raises:
        RuntimeError: If connection has not been initialized.
    """
    if _connection is None:
        raise RuntimeError(
            "DuckDB connection not initialized. Call init_connection() first."
        )
    return _connection


def init_connection() -> duckdb.DuckDBPyConnection:
    """Initialize and return the shared DuckDB connection.

    Called once at app startup (FastAPI lifespan).
    """
    global _connection
    if _connection is not None:
        return _connection

    _connection = duckdb.connect(str(settings.duckdb_path), read_only=False)
    _connection.execute("PRAGMA memory_limit='4GB'")
    return _connection


def close_connection() -> None:
    """Close the shared DuckDB connection.

    Called at app shutdown (FastAPI lifespan).
    """
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


@contextmanager
def get_connection_context(read_only: bool = False) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager for opening a fresh connection (for CLI/background tasks).

    Not used by the FastAPI app (which uses the shared connection),
    but useful for CLI commands and tests.

    Args:
        read_only: If True, open in read-only mode.

    Yields:
        A DuckDB connection.
    """
    conn = duckdb.connect(str(settings.duckdb_path), read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()
