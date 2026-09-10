from __future__ import annotations

from services.storage.postgres_account_storage import PostgresAccountStorageService
from services.storage.postgres_connection import get_pool
from services.storage.postgres_connection import init_pool
from services.storage.postgres_names_storage import PostgresNamesStorageServiceImpl
from services.storage.postgres_staging_storage import PostgresStagingStorageService
from services.storage.postgres_trace_storage import PostgresTraceStorageService

AccountStorageService = PostgresAccountStorageService
StagingStorageService = PostgresStagingStorageService
TraceStorageService = PostgresTraceStorageService
NamesStorageServiceImpl = PostgresNamesStorageServiceImpl

__all__ = [
    "AccountStorageService",
    "StagingStorageService",
    "TraceStorageService",
    "NamesStorageServiceImpl",
    "init_pool",
    "get_pool",
]
