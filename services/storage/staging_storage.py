from typing import Any

import duckdb
import logfire

from sales_intel.services.storage.duckdb_connection import get_pool
from sales_intel.services.storage.enums import StorageType, TableType
from sales_intel.services.storage.models import StagingRecord


class StagingStorageService:
    storage_type = StorageType.DATABASE
    table_type = TableType.STAGING_RECORDS

    def __init__(self, connection: duckdb.DuckDBPyConnection | None = None) -> None:
        self.connection = connection or get_pool().get_connection()

    def get(self, record_id: int) -> StagingRecord | None:
        row = self._fetch_one(
            "SELECT * FROM staging_records WHERE record_id = ?",
            {"record_id": record_id}
        )
        return StagingRecord(**row) if row else None

    def list(self, limit: int = 100, offset: int = 0) -> list[StagingRecord]:
        rows = self._fetch_all(
            "SELECT * FROM staging_records LIMIT ? OFFSET ?",
            {"limit": limit, "offset": offset}
        )
        return [StagingRecord(**row) for row in rows]

    def create(self, entity: StagingRecord) -> StagingRecord:
        raise NotImplementedError("Use bulk_insert for performance.")

    def update(self, entity: StagingRecord) -> StagingRecord:
        raise NotImplementedError("Staging records are immutable after insert.")

    def delete(self, record_id: int) -> bool:
        raise NotImplementedError("Staging records are not deleted.")

    def count(self) -> int:
        row = self._fetch_one("SELECT COUNT(*) as cnt FROM staging_records")
        return row["cnt"] if row else 0

    def bulk_insert(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        columns = list(records[0].keys())
        appender = duckdb.Appender(self.connection, "staging_records")

        inserted = 0
        for record in records:
            try:
                values = [record.get(col) for col in columns]
                appender.append(*values)
                inserted += 1
            except Exception as e:
                logfire.warning("staging_storage.insert_failed", error=str(e), record_id=record.get("record_id"))
                continue

        appender.close()
        return inserted

    def list_by_domain(self, root_domain: str, limit: int = 1000) -> list[StagingRecord]:
        rows = self._fetch_all(
            "SELECT * FROM staging_records WHERE root_domain = ? LIMIT ?",
            {"root_domain": root_domain, "limit": limit}
        )
        return [StagingRecord(**row) for row in rows]

    def _fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        result = self.connection.execute(query, params or {}).fetchall()
        return result[0] if result else None

    def _fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.connection.execute(query, params or {}).fetchall()
