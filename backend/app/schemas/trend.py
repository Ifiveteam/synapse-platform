"""트렌드 대시보드 API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.report import DashboardReportSchema


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
    report: DashboardReportSchema


class GraphViewResponse(BaseModel):
    cohort_size: int = Field(ge=0)
    axes: list[ProfileAxisSchema] = Field(min_length=8, max_length=8)


class AnalyzeRequest(BaseModel):
    email: EmailStr | None = Field(
        default=None,
        examples=["you@ifive.site"],
        description="분석 완료 시 결과 링크를 받을 이메일 (선택)",
    )


class AnalyzeResponse(BaseModel):
    post_id: str


class TrendPostSummarySchema(BaseModel):
    post_id: str
    generated_at: datetime
    cohort_size: int = Field(ge=0)


class TrendPostListResponse(BaseModel):
    items: list[TrendPostSummarySchema]
    total: int = Field(ge=0)


class TrendPostResponse(BaseModel):
    post_id: str
    generated_at: datetime
    cohort_size: int = Field(ge=0)
    axes: list[ProfileAxisSchema] = Field(min_length=8, max_length=8)
    report: DashboardReportSchema
