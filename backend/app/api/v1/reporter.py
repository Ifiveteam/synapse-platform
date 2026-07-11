"""Reporter — 지식 그래프·리포트·차트 B2B 조회 API."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.repositories import reporter_repository
from app.repositories.reporter_repository import MAX_SIMULATOR_RANGE_DAYS
from app.schemas.reporter import (
    GraphSimulatorRequest,
    GraphSimulatorResponse,
    HeatmapResponse,
    KnowledgeGraphResponse,
    MarkdownReportResponse,
    RunPipelineResponse,
    SnapshotInventoryDay,
    SnapshotInventoryResponse,
    StreamChartResponse,
    StreamSeriesPoint,
)
from app.services.graph_simulator_service import GraphSimulatorService
from app.services.trend_report_service import TrendReportService
from app.utils.report_filer import ReportFiler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reporter", tags=["reporter"])

KST = timezone(timedelta(hours=9))

_UNAVAILABLE_REPORT_TEMPLATE = """\
# 시냅스 트렌드 인텔리전스 리포트

**분석 기준일:** {target_date}

---

해당 일자의 리포트가 아직 생성되지 않았습니다.

- 일별 Reporter 배치 완료 후 다시 시도해 주세요.
- 문의: Synapse Intelligence Team
"""


def today_kst() -> date:
    """KST 기준 오늘 날짜."""
    return datetime.now(KST).date()


def _default_stream_start(end_date: date) -> date:
    """스트림 차트 기본 시작일 — 종료일 포함 최근 7일."""
    return end_date - timedelta(days=6)


def _parse_date_str(date_str: str) -> date:
    """YYYY-MM-DD 문자열을 date로 파싱한다. 실패 시 ValueError."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


@router.post("/run-pipeline", response_model=RunPipelineResponse)
async def run_reporter_pipeline(
    date_str: str = Query(
        ...,
        description="분석 대상 일자 (YYYY-MM-DD)",
        examples=["2026-07-07"],
    ),
    session: AsyncSession = Depends(get_db),
) -> RunPipelineResponse:
    """온디맨드 — 지식 그래프·마크다운 리포트 일별 파이프라인을 즉시 실행한다."""
    try:
        target_date = _parse_date_str(date_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"date_str 형식이 올바르지 않습니다. YYYY-MM-DD 로 전달해 주세요: {date_str}",
        ) from exc

    try:
        service = TrendReportService(session)
        result = await service.run_daily_pipeline(target_date)
    except Exception as exc:
        logger.exception(
            "[reporter][run-pipeline] 파이프라인 실패 target_date=%s",
            date_str,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reporter 파이프라인 실행 중 오류가 발생했습니다.",
        ) from exc

    graph_ok = result.graph.generated
    report_ok = result.report.generated
    return RunPipelineResponse(
        status="success",
        message=(
            f"{target_date.isoformat()} Reporter 파이프라인이 완료되었습니다 "
            f"(graph={'ok' if graph_ok else 'skipped'}, "
            f"report={'ok' if report_ok else 'skipped'})."
        ),
        target_date=target_date,
    )


@router.get("/snapshots", response_model=SnapshotInventoryResponse)
async def get_snapshot_inventory(
    end_date: date = Query(
        default_factory=today_kst,
        alias="date",
        description="KST 기준 조회 종료일 (YYYY-MM-DD)",
    ),
    days: int = Query(
        30,
        ge=1,
        le=MAX_SIMULATOR_RANGE_DAYS,
        description="종료일 포함 조회 일수 (기본 30일)",
    ),
    session: AsyncSession = Depends(get_db),
) -> SnapshotInventoryResponse:
    """관리자용 — 기간 내 일별 global_trends_snapshot 존재 여부와 요약을 반환한다."""
    start_date = end_date - timedelta(days=days - 1)
    items = await reporter_repository.fetch_snapshot_inventory(
        session,
        start_date,
        end_date,
    )
    days_out = [
        SnapshotInventoryDay(
            date=item.date,
            present=item.present,
            snapshot_id=item.snapshot_id,
            created_at=item.created_at,
            keyword_count=item.keyword_count,
            top_keywords=list(item.top_keywords),
            domain_keys=list(item.domain_keys),
        )
        for item in items
    ]
    present_count = sum(1 for item in days_out if item.present)
    return SnapshotInventoryResponse(
        start_date=start_date,
        end_date=end_date,
        present_count=present_count,
        missing_count=len(days_out) - present_count,
        days=days_out,
    )


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    graph_date: date = Query(
        default_factory=today_kst,
        alias="date",
        description="KST 기준 조회 종료일 (YYYY-MM-DD)",
    ),
    days: int = Query(
        14,
        ge=1,
        le=MAX_SIMULATOR_RANGE_DAYS,
        description="종료일 포함 롤업 일수 (기본 14일)",
    ),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeGraphResponse:
    """종료일 기준 N일 스냅샷을 롤업한 교차 도메인 지식 그래프를 반환한다.

    기본은 14일 합산. ``days=1`` 이면 해당 일자만 사용한다.
    """
    end_date = graph_date
    start_date = end_date - timedelta(days=days - 1)
    top_limit = 30 if days >= 7 else 20

    service = GraphSimulatorService(session)
    result = await service.simulate(
        GraphSimulatorRequest(
            start_date=start_date,
            end_date=end_date,
            top_keywords_limit=top_limit,
        )
    )
    return KnowledgeGraphResponse(
        nodes=result.nodes,
        links=result.links,
        start_date=start_date,
        end_date=end_date,
        snapshot_count=int(result.meta.get("snapshot_count") or 0),
    )


@router.get("/report", response_model=MarkdownReportResponse)
async def get_markdown_report(
    report_date: date = Query(
        default_factory=today_kst,
        alias="date",
        description="KST 기준 조회 일자 (YYYY-MM-DD)",
    ),
    session: AsyncSession = Depends(get_db),
) -> MarkdownReportResponse:
    """일별 B2B 마크다운 리포트를 반환한다.

    우선 ``ReportFiler`` 로컬 파일을 읽고, 없으면 DB ``b2b_trend_reports`` 를 조회한다.
    """
    filer = ReportFiler()
    markdown = await filer.read_report(report_date)
    if markdown and markdown.strip():
        return MarkdownReportResponse(markdown=markdown, source="file")

    db_markdown = await reporter_repository.fetch_b2b_report_markdown_by_date(
        session,
        report_date,
    )
    if db_markdown and db_markdown.strip():
        return MarkdownReportResponse(markdown=db_markdown, source="db")

    return MarkdownReportResponse(
        markdown=_UNAVAILABLE_REPORT_TEMPLATE.format(
            target_date=report_date.isoformat(),
        ),
        source="fallback",
    )


@router.get("/charts/stream", response_model=StreamChartResponse)
async def get_stream_chart_data(
    start_date: date | None = Query(
        default=None,
        description="KST 기준 시작일 (미지정 시 end_date 포함 최근 7일)",
    ),
    end_date: date = Query(
        default_factory=today_kst,
        description="KST 기준 종료일",
    ),
    session: AsyncSession = Depends(get_db),
) -> StreamChartResponse:
    """기간 내 일별 8축·도메인 가중치 시계열을 반환한다."""
    resolved_start = start_date or _default_stream_start(end_date)
    if resolved_start > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date는 end_date 이전이거나 같아야 합니다.",
        )

    snapshots = await reporter_repository.fetch_snapshots_by_date_range(
        session,
        resolved_start,
        end_date,
    )
    series = [
        StreamSeriesPoint(**reporter_repository.build_stream_series_point(row))
        for row in snapshots
    ]
    return StreamChartResponse(
        start_date=resolved_start,
        end_date=end_date,
        series=series,
    )


@router.get("/charts/heatmap", response_model=HeatmapResponse)
async def get_heatmap_chart_data(
    session: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    """최근 7일 행동·스크랩 빈도 히트맵 매트릭스를 반환한다."""
    matrix, max_count = await reporter_repository.fetch_activity_heatmap_counts(
        session,
    )
    return HeatmapResponse(
        days=reporter_repository.HEATMAP_DAYS,
        matrix=matrix,
        max_count=max_count,
    )


@router.post("/simulator/graph", response_model=GraphSimulatorResponse)
async def simulate_knowledge_graph(
    request: GraphSimulatorRequest,
    session: AsyncSession = Depends(get_db),
) -> GraphSimulatorResponse:
    """기간·도메인·스코어 필터로 지식 그래프를 On-the-fly 재연산한다."""
    service = GraphSimulatorService(session)
    return await service.simulate(request)
