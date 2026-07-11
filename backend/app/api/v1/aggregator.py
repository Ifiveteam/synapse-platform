"""어그리게이터(4 에이전트) API — 배치 수동 트리거 등."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.services.aggregator_scheduler import enqueue_daily_aggregation

router = APIRouter(prefix="/aggregator", tags=["aggregator"])


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_aggregator_batch(
    date_str: str | None = Query(
        default=None,
        description="집계 대상일 YYYY-MM-DD (미지정 시 KST 어제)",
        examples=["2026-06-30"],
    ),
) -> dict[str, str]:
    """로컬 개발·검증용 — 일별 배치 집계를 즉시 1회 백그라운드 실행한다."""
    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"date_str 형식이 올바르지 않습니다: {date_str}",
            ) from exc

    enqueue_daily_aggregation(target_date)
    label = target_date.isoformat() if target_date else "yesterday(KST)"
    return {
        "status": "success",
        "message": f"Aggregator batch job triggered manually ({label})",
    }
