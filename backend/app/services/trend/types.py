"""트렌드 게시판 서비스 내부 타입."""

from __future__ import annotations

from typing import TypedDict

from app.schemas.report import DashboardReportSchema


class TrendPostRecord(TypedDict):
    """인메모리 게시판 저장용 레코드."""

    post_id: str
    generated_at: str
    cohort_size: int
    report: DashboardReportSchema
