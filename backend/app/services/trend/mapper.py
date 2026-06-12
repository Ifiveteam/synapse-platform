"""AggregatorState ↔ 게시판 레코드 ↔ API 스키마 변환."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status

from app.agents.aggregator.report import coerce_dashboard_report
from app.agents.aggregator.state import AggregatorState
from app.schemas.trend import TrendPostResponse, TrendPostSummarySchema
from app.services.trend.types import TrendPostRecord


def require_report_from_state(state: AggregatorState):
    raw_report = state.get("report_json")
    if not raw_report:
        msg = "report_json이 AggregatorState에 없습니다."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
    return coerce_dashboard_report(raw_report)


def state_to_trend_post(
    state: AggregatorState,
    *,
    post_id: str | None = None,
) -> TrendPostRecord:
    """AggregatorState를 게시판 레코드로 변환한다."""
    integrated_data = state["integrated_data"]
    profile_map = integrated_data["internal_user_stats"]["cognitive_bias_map"]
    report = require_report_from_state(state)

    return {
        "post_id": post_id or state.get("post_id") or uuid.uuid4().hex,
        "generated_at": integrated_data["generated_at"],
        "cohort_size": profile_map["cohort_size"],
        "report": report,
    }


def to_post_summary(post: TrendPostRecord) -> TrendPostSummarySchema:
    return TrendPostSummarySchema(
        post_id=post["post_id"],
        generated_at=datetime.fromisoformat(post["generated_at"]),
        cohort_size=post["cohort_size"],
    )


def to_post_response(post: TrendPostRecord) -> TrendPostResponse:
    return TrendPostResponse(
        post_id=post["post_id"],
        generated_at=datetime.fromisoformat(post["generated_at"]),
        cohort_size=post["cohort_size"],
        report=post["report"],
    )
