"""트렌드 분석 대시보드 API 라우터."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.aggregator.mock_data import generate_internal_user_stats
from app.agents.aggregator.nodes import generate_b2b_report
from app.agents.aggregator.types import INTEGRATED_SCHEMA_VERSION, IntegratedData
from app.schemas.trend import (
    DashboardResponse,
    GraphViewResponse,
    KeywordStatSchema,
    ProfileAxisSchema,
)
from app.services import external_trends

router = APIRouter()


async def get_integrated_data() -> IntegratedData:
    """내부 Mock 통계와 외부 실시간 트렌드를 조립한 통합 데이터를 반환한다."""
    user_mock = generate_internal_user_stats()
    external_real = await external_trends.fetch_real_trends()

    return {
        "schema_version": INTEGRATED_SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "internal_user_stats": user_mock,
        "external_market_trends": external_real,
    }


async def get_b2b_report(
    data: Annotated[IntegratedData, Depends(get_integrated_data)],
) -> str:
    """Gemini 에이전트로 B2B 마크다운 리포트를 생성한다."""
    return await generate_b2b_report(data)


@router.get("/dashboard", response_model=DashboardResponse)
async def read_trend_dashboard(
    data: Annotated[IntegratedData, Depends(get_integrated_data)],
    report_markdown: Annotated[str, Depends(get_b2b_report)],
) -> DashboardResponse:
    """대시보드용 키워드 통계와 Gemini 리포트를 반환한다."""
    internal_stats = data["internal_user_stats"]
    generated_at = datetime.fromisoformat(data["generated_at"])

    return DashboardResponse(
        generated_at=generated_at,
        top_keywords=[
            KeywordStatSchema.model_validate(keyword)
            for keyword in internal_stats["top_keywords"]
        ],
        report_markdown=report_markdown,
    )


@router.get("/graph", response_model=GraphViewResponse)
async def read_trend_graph(
    data: Annotated[IntegratedData, Depends(get_integrated_data)],
) -> GraphViewResponse:
    """8각 인지 성향 차트용 코호트 분포 데이터를 반환한다."""
    profile_map = data["internal_user_stats"]["cognitive_bias_map"]

    return GraphViewResponse(
        cohort_size=profile_map["cohort_size"],
        axes=[
            ProfileAxisSchema.model_validate(axis) for axis in profile_map["axes"]
        ],
    )
