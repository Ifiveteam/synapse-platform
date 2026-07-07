"""어그리게이터(4 에이전트) API — 배치 수동 트리거 등."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.services.aggregator_scheduler import enqueue_daily_aggregation

router = APIRouter(prefix="/aggregator", tags=["aggregator"])


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_aggregator_batch() -> dict[str, str]:
    """로컬 개발·검증용 — 일별 배치 집계를 즉시 1회 백그라운드 실행한다."""
    enqueue_daily_aggregation()
    return {
        "status": "success",
        "message": "Aggregator batch job triggered manually",
    }
