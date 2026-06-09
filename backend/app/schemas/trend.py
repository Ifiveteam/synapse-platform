"""트렌드 대시보드 API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KeywordStatSchema(BaseModel):
    keyword: str
    frequency: int = Field(ge=0)
    trend_delta_pct: float


class ProfileAxisSchema(BaseModel):
    key: str
    label: str
    avg_score: float = Field(ge=0, le=100)


class DashboardResponse(BaseModel):
    generated_at: datetime
    top_keywords: list[KeywordStatSchema]
    report_markdown: str


class GraphViewResponse(BaseModel):
    cohort_size: int = Field(ge=0)
    axes: list[ProfileAxisSchema] = Field(min_length=8, max_length=8)


class AnalyzeResponse(BaseModel):
    post_id: str


class TrendPostResponse(BaseModel):
    post_id: str
    generated_at: datetime
    cohort_size: int = Field(ge=0)
    axes: list[ProfileAxisSchema] = Field(min_length=8, max_length=8)
    report_markdown: str
