from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from services.storage import TraceStorageService

router = APIRouter(prefix="/traces", tags=["traces"])


def get_trace_storage() -> TraceStorageService:
    return TraceStorageService()


@router.get("")
async def list_traces(
    task: str | None = Query(None, description="Filter by task name"),
    limit: int = Query(1000, ge=1, le=10000),
    storage: TraceStorageService = Depends(get_trace_storage),
) -> dict[str, Any]:
    """List LLM traces, optionally filtered by task."""
    traces = storage.list_traces(task=task, limit=limit)
    return {
        "total": len(traces),
        "limit": limit,
        "task_filter": task,
        "traces": traces,
    }


@router.get("/summary")
async def summarize_traces(
    storage: TraceStorageService = Depends(get_trace_storage),
) -> dict[str, Any]:
    """Get summary of LLM traces by task (cost, latency, count)."""
    summary = storage.summarize_traces()
    return {
        "summary": summary,
        "total_tasks": len(summary),
    }
