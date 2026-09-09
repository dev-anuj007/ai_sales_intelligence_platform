from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import duckdb

from sales_intel.config import settings
from sales_intel.services.storage.abstractions import ConnectionPool

_connection: duckdb.DuckDBPyConnection | None = None


class DuckDBConnectionPool:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = path or settings.duckdb_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.path), read_only=False)
            self._conn.execute("PRAGMA memory_limit='4GB'")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextmanager
    def context(self, read_only: bool = False) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        conn = duckdb.connect(str(self.path), read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()


_global_pool: DuckDBConnectionPool | None = None


def init_pool(path: Path | str | None = None) -> DuckDBConnectionPool:
    global _global_pool
    if _global_pool is None:
        _global_pool = DuckDBConnectionPool(path)
    return _global_pool


def get_pool() -> DuckDBConnectionPool:
    if _global_pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _global_pool


def close_pool() -> None:
    global _global_pool
    if _global_pool is not None:
        _global_pool.close()
        _global_pool = None
