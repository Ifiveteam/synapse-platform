"""Reporter — 지식 그래프 API 응답 스키마."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class KnowledgeGraphNode(BaseModel):
    """react-force-graph 노드 — graph_mapper 출력과 1:1 대응."""

    id: str
    group: str
    val: float = Field(ge=0)


class KnowledgeGraphLink(BaseModel):
    """react-force-graph 링크."""

    source: str
    target: str
    value: float = Field(ge=0)
    link_type: str | None = Field(
        default=None,
        description="cooccurrence | semantic | domain_hub",
    )
    similarity: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="semantic 링크 코사인 유사도",
    )


class KnowledgeGraphResponse(BaseModel):
    """지식 그래프 — 프론트엔드 즉시 바인딩 가능."""

    nodes: list[KnowledgeGraphNode] = Field(default_factory=list)
    links: list[KnowledgeGraphLink] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    snapshot_count: int | None = None


class MarkdownReportResponse(BaseModel):
    """일별 B2B 마크다운 리포트."""

    markdown: str
    source: str = Field(description="file | db | fallback")


class StreamSeriesPoint(BaseModel):
    """스트림그래프 일별 시계열 포인트."""

    date: date
    axes: dict[str, float] = Field(default_factory=dict)
    domains: dict[str, float] = Field(default_factory=dict)


class StreamChartResponse(BaseModel):
    """8축·도메인 시계열 스트림 데이터."""

    start_date: date
    end_date: date
    series: list[StreamSeriesPoint] = Field(default_factory=list)


class HeatmapResponse(BaseModel):
    """요일(0=월) × 시간(0~23) 활동 빈도 매트릭스."""

    days: int = 7
    day_labels: list[str] = Field(
        default_factory=lambda: ["월", "화", "수", "목", "금", "토", "일"],
    )
    matrix: list[list[int]] = Field(default_factory=list)
    max_count: int = 0


class GraphSimulatorRequest(BaseModel):
    """B2B 지식 그래프 시뮬레이터 요청."""

    start_date: date
    end_date: date
    target_domains: list[str] = Field(
        default_factory=list,
        description="필터 대상 TrendDomain 값 목록 (비우면 전체)",
    )
    min_score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        description="키워드 최소 스코어 컷오프",
    )
    top_keywords_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="그래프에 포함할 상위 키워드 수",
    )


class GraphSimulatorResponse(KnowledgeGraphResponse):
    """시뮬레이터 On-the-fly 그래프 + 메타."""

    meta: dict[str, object] = Field(default_factory=dict)


class RunPipelineResponse(BaseModel):
    """온디맨드 일별 Reporter 파이프라인 실행 결과."""

    status: str = "success"
    message: str
    target_date: date


class SnapshotInventoryDay(BaseModel):
    """관리자 — 일자별 스냅샷 인벤토리."""

    date: date
    present: bool
    snapshot_id: str | None = None
    created_at: datetime | None = None
    keyword_count: int = 0
    top_keywords: list[str] = Field(default_factory=list)
    domain_keys: list[str] = Field(default_factory=list)


class SnapshotInventoryResponse(BaseModel):
    """관리자 — 기간 스냅샷 인벤토리."""

    start_date: date
    end_date: date
    present_count: int
    missing_count: int
    days: list[SnapshotInventoryDay] = Field(default_factory=list)


class SnapshotKeywordRow(BaseModel):
    keyword: str
    score: float = 0
    count_today: int = 0
    rank: int = 0


class SnapshotDomainRow(BaseModel):
    domain: str
    user_count: int = 0
    total_duration: int = 0
    avg_weight: float = 0


class SnapshotSemanticLinkRow(BaseModel):
    source: str
    target: str
    similarity: float = 0
    link_type: str = "semantic"


class SnapshotDetailResponse(BaseModel):
    """관리자 — 단일 일자 스냅샷 상세."""

    date: date
    present: bool
    snapshot_id: str | None = None
    snapshot_date: datetime | None = None
    created_at: datetime | None = None
    keywords: list[SnapshotKeywordRow] = Field(default_factory=list)
    domains: list[SnapshotDomainRow] = Field(default_factory=list)
    axes: dict[str, float] = Field(default_factory=dict)
    semantic_link_count: int = 0
    semantic_links: list[SnapshotSemanticLinkRow] = Field(default_factory=list)
    external_keywords: list[str] = Field(default_factory=list)
    scrap_categories: list[str] = Field(default_factory=list)
    context_count: int = 0
    has_cross_domain_insights: bool = False
    report_source: str | None = None
    report_preview: str | None = None
    day_graph_nodes: int | None = None
    day_graph_links: int | None = None
