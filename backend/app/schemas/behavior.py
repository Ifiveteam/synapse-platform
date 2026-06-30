"""행동 데이터 수집 API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BehaviorLogCreate(BaseModel):
    """익스텐션 → POST /api/v1/tracking/events 요청 본문."""

    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., min_length=1, max_length=2048)
    page_title: str | None = Field(
        default=None,
        max_length=500,
        alias="pageTitle",
    )
    duration_seconds: int = Field(
        ...,
        ge=0,
        alias="durationSeconds",
    )
    timestamp: datetime


class BehaviorLogItem(BaseModel):
    """GET /api/v1/tracking/events 응답 항목."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    domain: str
    page_title: str | None
    duration_seconds: int
    timestamp: datetime


class BehaviorLogListResponse(BaseModel):
    """최근 행동 로그 목록."""

    items: list[BehaviorLogItem]


class DomainDurationStat(BaseModel):
    """Recharts PieChart/BarChart용 도메인별 체류 시간."""

    name: str
    value: int
    duration_seconds: int


class TodayStatsResponse(BaseModel):
    """오늘(KST) 유저 행동 통계."""

    total_duration_seconds: int
    top_domains: list[DomainDurationStat]
