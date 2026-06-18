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
    kind: str = "snapshot"


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem]
