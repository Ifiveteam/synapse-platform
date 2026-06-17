"""Profiler HTTP API 요청·응답."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.profiler.job import JobStatus
from app.services.notification import NotificationPayload


class AnalyzeResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING


class DbProfileResponse(BaseModel):
    """DB user_profile_history 스냅샷 (점수 + 해석)."""

    user_id: str
    snapshot_id: str
    snapshot_date: datetime
    scores: dict[str, float]
    summary_text: str
    persona_label: str | None = None
    behavior_reasoning: str | None = None
    dominant_traits: list[str] | None = None
    supporting_evidence: dict | None = None
    tone_of_user: str | None = None


class AnalysisListItem(BaseModel):
    """개인성향 분석 목록 한 행 (FE /me/analyses)."""

    id: str
    title: str
    snapshot_date: datetime | None = None
    status: str
    kind: str = "snapshot"


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem]


class JobResponse(BaseModel):
    job_id: str
    user_id: str
    status: JobStatus
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    result: DbProfileResponse | None = None
    error: str | None = None
    notification: NotificationPayload | None = None
