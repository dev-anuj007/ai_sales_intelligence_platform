from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from services.enrichment.service import EnrichmentService
from services.storage import get_pool

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


def get_enrichment_service() -> EnrichmentService:
    pool = get_pool()
    conn = pool.get_connection()
    return EnrichmentService(conn)


@router.post("/run")
async def run_enrichment(
    top_n: int = 50,
    score_version: str = "v1",
    service: EnrichmentService = Depends(get_enrichment_service),
) -> dict[str, Any]:
    return service.enrich_top_accounts(top_n=top_n, score_version=score_version)
