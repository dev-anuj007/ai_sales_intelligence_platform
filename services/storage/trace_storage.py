from typing import Any

import duckdb
import logfire

from sales_intel.services.storage.duckdb_connection import get_pool
from sales_intel.services.storage.enums import StorageType, TableType


class TraceStorageService:
    storage_type = StorageType.DATABASE
    table_type = TableType.TRACE_LOGS

    def __init__(self, connection: duckdb.DuckDBPyConnection | None = None) -> None:
        self.connection = connection or get_pool().get_connection()

    def append_trace(self, trace_record: dict[str, Any]) -> None:
        columns = list(trace_record.keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)

        query = f"INSERT INTO trace_logs ({column_names}) VALUES ({placeholders})"
        values = [trace_record[col] for col in columns]

        try:
            self.connection.execute(query, values)
            logfire.info("trace_storage.appended", trace_id=trace_record.get("trace_id"))
        except Exception as e:
            logfire.error("trace_storage.append_failed", error=str(e))
            raise

    def list_traces(self, task: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        if task:
            query = "SELECT * FROM trace_logs WHERE task = ? ORDER BY timestamp DESC LIMIT ?"
            params = {"task": task, "limit": limit}
        else:
            query = "SELECT * FROM trace_logs ORDER BY timestamp DESC LIMIT ?"
            params = {"limit": limit}

        return self._fetch_all(query, params)

    def summarize_traces(self) -> dict[str, Any]:
        query = """
            SELECT
                task,
                COUNT(*) as count,
                AVG(CAST(cost_usd AS FLOAT)) as avg_cost_usd,
                SUM(CAST(cost_usd AS FLOAT)) as total_cost_usd,
                AVG(CAST(latency_ms AS INTEGER)) as avg_latency_ms
            FROM trace_logs
            GROUP BY task
            ORDER BY total_cost_usd DESC
        """
        rows = self._fetch_all(query)
        return {row["task"]: row for row in rows}

    def _fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        result = self.connection.execute(query, params or {}).fetchall()
        return result[0] if result else None

    def _fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.connection.execute(query, params or {}).fetchall()
