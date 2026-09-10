from __future__ import annotations

from typing import Any

import logfire
from sqlalchemy import desc
from sqlalchemy.orm import Session

from services.storage.enums import StorageType, TableType
from services.storage.postgres_connection import get_pool
from services.storage.sqlmodel_models import TraceRecordSQL


class PostgresTraceStorageService:
    """PostgreSQL implementation of trace storage using SQLModel."""

    storage_type = StorageType.DATABASE
    table_type = TableType.TRACE_LOGS

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self._owns_session = session is None

    def _get_session(self) -> Session:
        """Get or create a session."""
        if self.session is not None:
            return self.session
        return get_pool().get_connection()

    def append_trace(self, trace_record: dict[str, Any]) -> None:
        """Append a trace record."""
        session = self._get_session()
        try:
            trace_sql = TraceRecordSQL(**trace_record)
            session.add(trace_sql)
            session.commit()
            logfire.info("trace_storage.appended", trace_id=trace_record.get("trace_id"))
        except Exception as e:
            logfire.error("trace_storage.append_failed", error=str(e))
            raise
        finally:
            if self._owns_session:
                session.close()

    def list_traces(self, task: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        """List traces, optionally filtered by task."""
        session = self._get_session()
        try:
            query = session.query(TraceRecordSQL)

            if task:
                query = query.filter(TraceRecordSQL.task == task)

            traces_sql = query.order_by(desc(TraceRecordSQL.timestamp)).limit(limit).all()
            return [self._to_dict(t) for t in traces_sql]
        finally:
            if self._owns_session:
                session.close()

    def summarize_traces(self) -> dict[str, Any]:
        """Summarize traces by task."""
        session = self._get_session()
        try:
            from sqlalchemy import func

            traces_sql = (
                session.query(
                    TraceRecordSQL.task,
                    func.count(TraceRecordSQL.trace_id).label("count"),
                    func.avg(TraceRecordSQL.cost_usd).label("avg_cost_usd"),
                    func.sum(TraceRecordSQL.cost_usd).label("total_cost_usd"),
                    func.avg(TraceRecordSQL.latency_ms).label("avg_latency_ms"),
                )
                .group_by(TraceRecordSQL.task)
                .order_by(desc("total_cost_usd"))
                .all()
            )

            result = {}
            for row in traces_sql:
                result[row.task] = {
                    "task": row.task,
                    "count": row.count,
                    "avg_cost_usd": float(row.avg_cost_usd) if row.avg_cost_usd else 0.0,
                    "total_cost_usd": float(row.total_cost_usd) if row.total_cost_usd else 0.0,
                    "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else 0.0,
                }
            return result
        finally:
            if self._owns_session:
                session.close()

    @staticmethod
    def _to_dict(trace_sql: TraceRecordSQL) -> dict[str, Any]:
        """Convert SQLModel to dict."""
        return {
            "trace_id": trace_sql.trace_id,
            "timestamp": trace_sql.timestamp,
            "task": trace_sql.task,
            "root_domain": trace_sql.root_domain,
            "model": trace_sql.model,
            "prompt_name": trace_sql.prompt_name,
            "prompt_version": trace_sql.prompt_version,
            "input_tokens": trace_sql.input_tokens,
            "output_tokens": trace_sql.output_tokens,
            "cost_usd": trace_sql.cost_usd,
            "latency_ms": trace_sql.latency_ms,
            "decision": trace_sql.decision,
            "success": trace_sql.success,
            "error": trace_sql.error,
            "request_hash": trace_sql.request_hash,
            "llm_client_type": trace_sql.llm_client_type,
        }
