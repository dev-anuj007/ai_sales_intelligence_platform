from __future__ import annotations

from config import settings

if settings.db_type == "postgres":
    from services.storage.postgres_account_storage import PostgresAccountStorageService
    from services.storage.postgres_connection import get_pool as get_postgres_pool
    from services.storage.postgres_connection import init_pool as init_postgres_pool
    from services.storage.postgres_names_storage import PostgresNamesStorageServiceImpl
    from services.storage.postgres_staging_storage import PostgresStagingStorageService
    from services.storage.postgres_trace_storage import PostgresTraceStorageService

    AccountStorageService = PostgresAccountStorageService  # type: ignore
    StagingStorageService = PostgresStagingStorageService  # type: ignore
    TraceStorageService = PostgresTraceStorageService  # type: ignore
    NamesStorageServiceImpl = PostgresNamesStorageServiceImpl  # type: ignore
    init_pool = init_postgres_pool  # type: ignore
    get_pool = get_postgres_pool  # type: ignore
else:
    # DuckDB fallback
    from services.storage.account_storage import AccountStorageService
    from services.storage.duckdb_connection import get_pool
    from services.storage.duckdb_connection import init_pool
    from services.storage.names_storage import NamesStorageServiceImpl
    from services.storage.staging_storage import StagingStorageService
    from services.storage.trace_storage import TraceStorageService


__all__ = [
    "AccountStorageService",
    "StagingStorageService",
    "TraceStorageService",
    "NamesStorageServiceImpl",
    "init_pool",
    "get_pool",
]
