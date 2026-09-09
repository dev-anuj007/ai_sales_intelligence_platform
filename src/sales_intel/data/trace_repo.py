"""Repository for LLM trace logs (observability, cost tracking).

Traces are appended to a JSONL file and also queryable via DuckDB.
"""

import json
from datetime import datetime
from pathlib import Path

import duckdb
import logfire

from sales_intel.config import settings
from sales_intel.data.models import TraceRecord
from sales_intel.data.repository import BaseRepository


class TraceRepository(BaseRepository[TraceRecord]):
    """Repository for LLM call traces.

    Traces are written to a JSONL file (traces/llm_traces.jsonl) for durable logging
    and are also queryable via DuckDB for analytics.
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Initialize trace repository.

        Args:
            connection: DuckDB connection (used for analytics queries only).
        """
        super().__init__(connection)
        self.traces_path = settings.traces_jsonl_path
        self.traces_path.parent.mkdir(parents=True, exist_ok=True)

    def get_by_id(self, id_value: str) -> TraceRecord | None:
        """Retrieve a trace by trace_id.

        Reads from the JSONL file.
        """
        if not self.traces_path.exists():
            return None

        for line in self.traces_path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("trace_id") == id_value:
                return TraceRecord(**record)

        return None

    def list(self, limit: int = 100, offset: int = 0) -> list[TraceRecord]:
        """List traces from the JSONL file with pagination."""
        if not self.traces_path.exists():
            return []

        traces: list[TraceRecord] = []
        count = 0

        for line in self.traces_path.read_text().splitlines():
            if not line.strip():
                continue
            if count < offset:
                count += 1
                continue
            if len(traces) >= limit:
                break

            record = json.loads(line)
            traces.append(TraceRecord(**record))
            count += 1

        return traces

    def create(self, entity: TraceRecord) -> TraceRecord:
        """Append a trace to the JSONL file."""
        self.append_trace(entity)
        return entity

    def update(self, entity: TraceRecord) -> TraceRecord:
        """Traces are immutable once written."""
        raise NotImplementedError("Traces are immutable.")

    def delete(self, id_value: str) -> bool:
        """Traces are never deleted."""
        raise NotImplementedError("Traces are never deleted.")

    def append_trace(self, trace: TraceRecord) -> None:
        """Append a trace record as a JSON line.

        Args:
            trace: TraceRecord to append.
        """
        line = json.dumps(trace.model_dump(mode="json"), default=str) + "\n"
        self.traces_path.append_text(line)
        logfire.info("trace_repo.trace_appended", task=trace.task, trace_id=trace.trace_id)

    def list_by_task(self, task: str, limit: int = 100) -> list[TraceRecord]:
        """List traces filtered by task name."""
        if not self.traces_path.exists():
            return []

        traces: list[TraceRecord] = []

        for line in self.traces_path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("task") == task:
                traces.append(TraceRecord(**record))
                if len(traces) >= limit:
                    break

        return traces

    def list_by_root_domain(self, root_domain: str, limit: int = 100) -> list[TraceRecord]:
        """List traces for a specific account."""
        if not self.traces_path.exists():
            return []

        traces: list[TraceRecord] = []

        for line in self.traces_path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("root_domain") == root_domain:
                traces.append(TraceRecord(**record))
                if len(traces) >= limit:
                    break

        return traces

    def get_cost_summary(self) -> dict[str, object]:
        """Get cost summary across all traces.

        Returns a dict with task, model, and total cost statistics.
        Queries via DuckDB's read_json_auto() for efficiency.

        Returns:
            Dict with keys like 'total_cost_usd', 'by_task', 'by_model'.
        """
        if not self.traces_path.exists():
            return {"total_cost_usd": 0.0, "by_task": {}, "by_model": {}, "count": 0}

        try:
            result = self.connection.execute(
                f"""
                SELECT
                    SUM(cost_usd) as total_cost,
                    COUNT(*) as total_count,
                    task,
                    model
                FROM read_json_auto('{self.traces_path}')
                GROUP BY task, model
                ORDER BY total_cost DESC
                """
            )

            rows = result.fetchall()
            if not rows:
                return {"total_cost_usd": 0.0, "by_task": {}, "by_model": {}, "count": 0}

            summary: dict[str, object] = {
                "total_cost_usd": 0.0,
                "total_count": 0,
                "by_task": {},
                "by_model": {},
            }

            for row in rows:
                total_cost, count, task, model = row
                summary["total_cost_usd"] = float(summary.get("total_cost_usd", 0)) + (total_cost or 0.0)
                summary["total_count"] = int(summary.get("total_count", 0)) + (count or 0)

                if task not in summary.get("by_task", {}):
                    summary.setdefault("by_task", {})[task] = {  # type: ignore
                        "cost": 0.0,
                        "count": 0,
                    }
                summary["by_task"][task]["cost"] = (  # type: ignore
                    float(summary["by_task"][task]["cost"]) + (total_cost or 0.0)  # type: ignore
                )
                summary["by_task"][task]["count"] = (  # type: ignore
                    int(summary["by_task"][task]["count"]) + (count or 0)  # type: ignore
                )

                if model not in summary.get("by_model", {}):
                    summary.setdefault("by_model", {})[model] = {  # type: ignore
                        "cost": 0.0,
                        "count": 0,
                    }
                summary["by_model"][model]["cost"] = (  # type: ignore
                    float(summary["by_model"][model]["cost"]) + (total_cost or 0.0)  # type: ignore
                )
                summary["by_model"][model]["count"] = (  # type: ignore
                    int(summary["by_model"][model]["count"]) + (count or 0)  # type: ignore
                )

            return summary
        except Exception as e:
            logfire.warning("trace_repo.get_cost_summary_failed", error=str(e))
            return {"total_cost_usd": 0.0, "by_task": {}, "by_model": {}, "count": 0}
