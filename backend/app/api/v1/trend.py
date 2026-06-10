"""트렌드 분석 대시보드 API 라우터."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from app.agents.aggregator.agent import assemble_integrated_data, get_aggregator_agent
from app.agents.aggregator.base import IntegratedData, ProfileAxisScore
from app.schemas.trend import (
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
    report_markdown: str


# 가상 인메모리 게시판 저장소 (post_id → 게시글)
_TREND_POSTS: dict[str, TrendPostRecord] = {}


async def get_integrated_data() -> IntegratedData:
    """내부 Mock 통계와 외부 실시간 트렌드를 조립한 통합 데이터를 반환한다."""
    return await assemble_integrated_data()


async def get_b2b_report(
    data: Annotated[IntegratedData, Depends(get_integrated_data)],
) -> str:
    """Gemini 에이전트로 B2B 마크다운 리포트를 생성한다."""
    agent = get_aggregator_agent()
    return await agent.generate_report(data)


async def _create_trend_post() -> TrendPostRecord:
    """통합 데이터를 조립하고 Gemini 리포트를 생성한 뒤 게시글 레코드를 만든다."""
    agent = get_aggregator_agent()
    data = await agent.assemble_integrated_data()
    report_markdown = await agent.generate_report(data)
    profile_map = data["internal_user_stats"]["cognitive_bias_map"]

    return {
        "post_id": uuid.uuid4().hex,
        "generated_at": data["generated_at"],
        "cohort_size": profile_map["cohort_size"],
        "axes": profile_map["axes"],
        "report_markdown": report_markdown,
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
        report_markdown=post["report_markdown"],
    )


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_201_CREATED)
async def analyze_trend() -> AnalyzeResponse:
    """트렌드 분석을 실행하고 결과를 인메모리 게시판에 저장한다."""
    post = await _create_trend_post()
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
    """저장된 분석 게시글의 8각 축 점수와 마크다운 본문을 반환한다."""
    return _to_post_response(_get_post_or_404(post_id))


@router.get("/posts/{post_id}/download")
async def download_trend_post_pdf(post_id: str) -> StreamingResponse:
    """저장된 마크다운 본문을 PDF로 변환하여 스트리밍 다운로드한다."""
    post = _get_post_or_404(post_id)
    pdf_bytes = await convert_markdown_to_pdf_async(post["report_markdown"])
    filename = f"B2B_Trend_Report_{post_id[:8]}_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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


@router.get("/download-pdf")
async def download_trend_report_pdf(
    report_markdown: Annotated[str, Depends(get_b2b_report)],
) -> Response:
    """Gemini 리포트 Markdown을 B2B PDF로 변환하여 다운로드한다."""
    pdf_bytes = await convert_markdown_to_pdf_async(report_markdown)
    filename = f"B2B_Trend_Report_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
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
