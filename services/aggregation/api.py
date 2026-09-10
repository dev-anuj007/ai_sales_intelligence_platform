from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from services.aggregation.service import AggregationService

router = APIRouter(prefix="/aggregation", tags=["aggregation"])


def get_aggregation_service() -> AggregationService:
	return AggregationService()


@router.post("/run")
async def run_aggregation(service: AggregationService = Depends(get_aggregation_service)) -> dict[str, Any]:
	return await service.aggregate_staging_to_accounts()
