from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile

from services.pipeline.service import IngestService
from services.storage import StagingStorageService, get_pool

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def get_ingest_service() -> IngestService:
    pool = get_pool()
    conn = pool.get_connection()
    staging_storage = StagingStorageService(conn)
    return IngestService(staging_storage)


@router.post("/ingest")
async def ingest_records(
    input_path: str,
    batch_size: int = 5000,
    limit: int | None = None,
    service: IngestService = Depends(get_ingest_service),
) -> dict[str, Any]:
    return service.ingest(Path(input_path), batch_size=batch_size, limit=limit)
