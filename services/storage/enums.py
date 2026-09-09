from enum import Enum


class StorageType(Enum):
    DATABASE = "database"
    CACHE = "cache"
    FILE = "file"


class TableType(Enum):
    ACCOUNTS = "accounts"
    STAGING_RECORDS = "staging_records"
    ACCOUNT_TOP_RECORDS = "account_top_records"
    TRACE_LOGS = "trace_logs"
