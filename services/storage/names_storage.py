from datetime import datetime
from typing import Any

import duckdb
import logfire

from sales_intel.services.storage.abstractions import NamesStorageService
from sales_intel.services.storage.duckdb_connection import get_pool
from sales_intel.services.storage.enums import StorageType, TableType


class NamesStorageServiceImpl:
    storage_type = StorageType.DATABASE
    table_type = TableType.ACCOUNTS

    def __init__(self, connection: duckdb.DuckDBPyConnection | None = None) -> None:
        self.connection = connection or get_pool().get_connection()
        self._cache: dict[str, str] = {}

    def store_name(self, root_domain: str, company_name: str, source: str) -> None:
        query = """
            UPDATE accounts
            SET inferred_company_name = ?, enriched_at = ?
            WHERE root_domain = ?
        """
        self.connection.execute(query, [company_name, datetime.utcnow(), root_domain])
        self._cache[root_domain] = company_name
        logfire.info("names_storage.stored", root_domain=root_domain, source=source)

    def get_name(self, root_domain: str) -> str | None:
        if root_domain in self._cache:
            return self._cache[root_domain]

        row = self._fetch_one(
            "SELECT inferred_company_name FROM accounts WHERE root_domain = ?",
            [root_domain]
        )

        if row and row.get("inferred_company_name"):
            name = row["inferred_company_name"]
            self._cache[root_domain] = name
            return name

        return None

    def list_by_pattern(self, pattern: str, limit: int = 100) -> dict[str, str]:
        rows = self._fetch_all(
            "SELECT root_domain, inferred_company_name FROM accounts "
            "WHERE inferred_company_name ILIKE ? AND inferred_company_name IS NOT NULL "
            "LIMIT ?",
            [f"%{pattern}%", limit]
        )
        result = {}
        for row in rows:
            if row.get("inferred_company_name"):
                result[row["root_domain"]] = row["inferred_company_name"]
                self._cache[row["root_domain"]] = row["inferred_company_name"]
        return result

    def clear_cache(self) -> None:
        self._cache.clear()
        logfire.info("names_storage.cache_cleared")

    def _fetch_one(self, query: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        result = self.connection.execute(query, params or []).fetchall()
        return result[0] if result else None

    def _fetch_all(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        return self.connection.execute(query, params or []).fetchall()
