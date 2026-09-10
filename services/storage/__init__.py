from services.storage.enums import StorageType, TableType
from services.storage.factory import (
    AccountStorageService,
    NamesStorageServiceImpl,
    StagingStorageService,
    TraceStorageService,
    get_pool,
    init_pool,
)
from services.storage.models import Account, StagingRecord

try:
    from services.storage.duckdb_connection import DuckDBConnectionPool
except ImportError:
    DuckDBConnectionPool = None  # type: ignore


def close_pool() -> None:
    """Close the connection pool."""
    from services.storage.factory import get_pool
    pool = get_pool()
    pool.close()


__all__ = [
    "StorageType",
    "TableType",
    "Account",
    "StagingRecord",
    "DuckDBConnectionPool",
    "AccountStorageService",
    "StagingStorageService",
    "TraceStorageService",
    "NamesStorageServiceImpl",
    "init_pool",
    "get_pool",
    "close_pool",
]
