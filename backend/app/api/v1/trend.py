"""트렌드 분석 대시보드 API 라우터."""

from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents.aggregator.agent import get_aggregator_agent
from app.schemas.trend import (
    AnalyzeRequest,
    AnalyzeResponse,
    TrendPostListResponse,
    TrendPostResponse,
)
from app.services.trend import (
    build_trend_report_pdf,
    get_post,
    list_posts,
    save_post,
    state_to_trend_post,
    to_post_response,
    to_post_summary,
    trend_report_pdf_filename,
)

router = APIRouter()


@router.post(
    "/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_201_CREATED
)
async def analyze_trend(body: AnalyzeRequest | None = None) -> AnalyzeResponse:
    """트렌드 분석을 실행하고 결과를 인메모리 게시판에 저장한다."""
    request = body or AnalyzeRequest()
    post_id = uuid.uuid4().hex
    agent = get_aggregator_agent()
    state = await agent.run(
        notify_email=str(request.email) if request.email else None,
        post_id=post_id,
    )
    post = state_to_trend_post(state, post_id=post_id)
    save_post(post)
    return AnalyzeResponse(post_id=post["post_id"])


@router.get("/posts", response_model=TrendPostListResponse)
async def list_trend_posts() -> TrendPostListResponse:
    """저장된 분석 게시글 목록을 최신순으로 반환한다."""
    items = sorted(
        (to_post_summary(post) for post in list_posts()),
        key=lambda item: item.generated_at,
        reverse=True,
    )
    return TrendPostListResponse(items=items, total=len(items))


@router.get("/posts/{post_id}", response_model=TrendPostResponse)
async def read_trend_post(post_id: str) -> TrendPostResponse:
    """저장된 분석 게시글의 구조화 리포트 JSON을 반환한다."""
    post = get_post(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post_id '{post_id}'에 해당하는 분석 게시글을 찾을 수 없습니다.",
        )
    return to_post_response(post)


@router.get("/posts/{post_id}/download")
async def download_trend_post_pdf(post_id: str) -> StreamingResponse:
    """저장된 구조화 리포트를 PDF로 스트리밍 다운로드한다."""
    post = get_post(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"post_id '{post_id}'에 해당하는 분석 게시글을 찾을 수 없습니다.",
        )

    pdf_bytes = await build_trend_report_pdf(post["report"])
    filename = trend_report_pdf_filename(post_id=post_id)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
