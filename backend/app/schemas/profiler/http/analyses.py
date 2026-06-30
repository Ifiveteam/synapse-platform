"""분석 목록 HTTP 응답."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AnalysisListItem(BaseModel):
    """개인성향 분석 목록 한 행 (FE /me/analyses)."""

    id: str
    title: str
    snapshot_date: datetime | None = None
    status: str
    stage: str | None = None  # running일 때: "indexing"(분류) | "profiling"(분석)
    kind: str = "snapshot"


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem]
