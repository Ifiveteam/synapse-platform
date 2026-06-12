"""트렌드 분석 대시보드 API 라우터."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from app.agents.aggregator.agent import get_aggregator_agent
from app.agents.aggregator.base import ProfileAxisScore
from app.agents.aggregator.report import coerce_dashboard_report, dashboard_report_to_markdown
from app.agents.aggregator.state import AggregatorState
from app.schemas.report import DashboardReportSchema
from app.schemas.trend import (
    AnalyzeRequest,
    AnalyzeResponse,
    DashboardResponse,
    GraphViewResponse,
    KeywordStatSchema,
    ProfileAxisSchema,
    TrendPostListResponse,
    TrendPostResponse,
    TrendPostSummarySchema,
)
from app.services.pdf import convert_markdown_to_pdf_async

router = APIRouter()


class TrendPostRecord(TypedDict):
    """인메모리 게시판 저장용 레코드 (API 라우터 private)."""

    post_id: str
    generated_at: str
    cohort_size: int
    axes: list[ProfileAxisScore]
    report: DashboardReportSchema


# 가상 인메모리 게시판 저장소 (post_id → 게시글)
_TREND_POSTS: dict[str, TrendPostRecord] = {}


async def get_aggregator_state() -> AggregatorState:
    """LangGraph 멀티 에이전트 전체 워크플로우를 실행하고 상태를 반환한다."""
    agent = get_aggregator_agent()
    return await agent.run()


async def get_assembled_state() -> AggregatorState:
    """데이터 조립 서브그래프만 실행한다. Gemini 호출 없이 integrated_data만 반환."""
    agent = get_aggregator_agent()
    return await agent.run_assemble_only()


def _require_report(state: AggregatorState) -> DashboardReportSchema:
    raw_report = state.get("report_json")
    if not raw_report:
        msg = "report_json이 AggregatorState에 없습니다."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
    return coerce_dashboard_report(raw_report)


def _state_to_trend_post(
    state: AggregatorState,
    *,
    post_id: str | None = None,
) -> TrendPostRecord:
    """AggregatorState를 게시판 레코드로 변환한다."""
    integrated_data = state["integrated_data"]
    profile_map = integrated_data["internal_user_stats"]["cognitive_bias_map"]
    report = _require_report(state)

    return {
        "post_id": post_id or state.get("post_id") or uuid.uuid4().hex,
        "generated_at": integrated_data["generated_at"],
        "cohort_size": profile_map["cohort_size"],
        "axes": profile_map["axes"],
        "report": report,
    }


def _get_post_or_404(post_id: str) -> TrendPostRecord:
    post = _TREND_POSTS.get(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post_id '{post_id}'에 해당하는 분석 게시글을 찾을 수 없습니다.",
        )
    return post


def _to_post_summary(post: TrendPostRecord) -> TrendPostSummarySchema:
    return TrendPostSummarySchema(
        post_id=post["post_id"],
        generated_at=datetime.fromisoformat(post["generated_at"]),
        cohort_size=post["cohort_size"],
    )


def _to_post_response(post: TrendPostRecord) -> TrendPostResponse:
    return TrendPostResponse(
        post_id=post["post_id"],
        generated_at=datetime.fromisoformat(post["generated_at"]),
        cohort_size=post["cohort_size"],
        axes=[ProfileAxisSchema.model_validate(axis) for axis in post["axes"]],
        report=post["report"],
    )


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_201_CREATED)
async def analyze_trend(body: AnalyzeRequest | None = None) -> AnalyzeResponse:
    """트렌드 분석을 실행하고 결과를 인메모리 게시판에 저장한다."""
    request = body or AnalyzeRequest()
    post_id = uuid.uuid4().hex
    agent = get_aggregator_agent()
    state = await agent.run(
        notify_email=str(request.email) if request.email else None,
        post_id=post_id,
    )
    post = _state_to_trend_post(state, post_id=post_id)
    _TREND_POSTS[post["post_id"]] = post
    return AnalyzeResponse(post_id=post["post_id"])


@router.get("/posts", response_model=TrendPostListResponse)
async def list_trend_posts() -> TrendPostListResponse:
    """저장된 분석 게시글 목록을 최신순으로 반환한다."""
    items = sorted(
        (_to_post_summary(post) for post in _TREND_POSTS.values()),
        key=lambda item: item.generated_at,
        reverse=True,
    )
    return TrendPostListResponse(items=items, total=len(items))


@router.get("/posts/{post_id}", response_model=TrendPostResponse)
async def read_trend_post(post_id: str) -> TrendPostResponse:
    """저장된 분석 게시글의 8각 축 점수와 구조화 리포트 JSON을 반환한다."""
    return _to_post_response(_get_post_or_404(post_id))


@router.get("/posts/{post_id}/download")
async def download_trend_post_pdf(post_id: str) -> StreamingResponse:
    """저장된 구조화 리포트를 Markdown으로 변환 후 PDF로 스트리밍 다운로드한다."""
    post = _get_post_or_404(post_id)
    markdown = dashboard_report_to_markdown(post["report"])
    pdf_bytes = await convert_markdown_to_pdf_async(markdown)
    filename = f"B2B_Trend_Report_{post_id[:8]}_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def read_trend_dashboard(
    state: Annotated[AggregatorState, Depends(get_aggregator_state)],
) -> DashboardResponse:
    """대시보드용 키워드 통계와 구조화 Gemini 리포트를 반환한다."""
    integrated_data = state["integrated_data"]
    internal_stats = integrated_data["internal_user_stats"]
    generated_at = datetime.fromisoformat(integrated_data["generated_at"])

    return DashboardResponse(
        generated_at=generated_at,
        top_keywords=[
            KeywordStatSchema.model_validate(keyword)
            for keyword in internal_stats["top_keywords"]
        ],
        report=_require_report(state),
    )


@router.get("/download-pdf")
async def download_trend_report_pdf(
    state: Annotated[AggregatorState, Depends(get_aggregator_state)],
) -> Response:
    """구조화 리포트를 Markdown으로 변환 후 B2B PDF로 다운로드한다."""
    report = _require_report(state)
    pdf_bytes = await convert_markdown_to_pdf_async(dashboard_report_to_markdown(report))
    filename = f"B2B_Trend_Report_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/graph", response_model=GraphViewResponse)
async def read_trend_graph(
    state: Annotated[AggregatorState, Depends(get_assembled_state)],
) -> GraphViewResponse:
    """8각 인지 성향 차트용 코호트 분포 데이터를 반환한다. (데이터 조립만 실행)"""
    profile_map = state["integrated_data"]["internal_user_stats"]["cognitive_bias_map"]

    return GraphViewResponse(
        cohort_size=profile_map["cohort_size"],
        axes=[
            ProfileAxisSchema.model_validate(axis) for axis in profile_map["axes"]
        ],
    )
