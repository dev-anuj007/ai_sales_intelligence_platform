from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from services.scoring.service import ScoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])


def get_scoring_service() -> ScoringService:
    return ScoringService()


@router.post("/run")
async def run_scoring(
    score_version: str = "v1",
    service: ScoringService = Depends(get_scoring_service),
) -> dict[str, Any]:
    return await service.score_accounts(score_version=score_version)
