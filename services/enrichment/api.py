from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from services.enrichment.service import EnrichmentService

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


def get_enrichment_service() -> EnrichmentService:
	return EnrichmentService()


@router.post("/run")
async def run_enrichment(
    top_n: int = 50,
    service: EnrichmentService = Depends(get_enrichment_service),
) -> dict[str, Any]:
    return await service.enrich_top_accounts(top_n=top_n)
