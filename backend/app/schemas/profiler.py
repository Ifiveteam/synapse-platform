"""Profiler API Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.agents.profiler.base import (
    AnomalyItem,
    BehaviorPatterns,
    JobStatus,
    LayerB,
    NotificationPayload,
    PersonaInfo,
    ProfileCompareDelta,
    ProfilerSnapshot,
    Synapse8Axes,
    Top5Interest,
)


class AnalyzeRequest(BaseModel):
    user_id: str = Field(..., examples=["mock_minsu"])
    email: EmailStr = Field(..., examples=["you@ifive.site"])


class AnalyzeResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING


class ProfileInterpretationResponse(BaseModel):
    consumption_mode: str
    primary_lever: str
    sovereignty_verdict: str
    radar_gap_insight: str


class ProfilerResultResponse(BaseModel):
    user_id: str
    computed_at: datetime
    axes: Synapse8Axes
    layer_b: LayerB
    top5_interests: list[Top5Interest]
    summary: str
    interpretation: ProfileInterpretationResponse
    axis_notes: dict[str, str] = Field(default_factory=dict)
    investigation_log: list[str] = Field(default_factory=list)
    llm_used: bool = False
    behavior_patterns: BehaviorPatterns | None = None


class JobResponse(BaseModel):
    job_id: str
    user_id: str
    status: JobStatus
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    result: ProfilerResultResponse | None = None
    error: str | None = None
    notification: NotificationPayload | None = None


class PersonasResponse(BaseModel):
    personas: list[PersonaInfo]


class SnapshotListResponse(BaseModel):
    user_id: str
    versions: list[str]


class SnapshotResponse(BaseModel):
    snapshot: ProfilerSnapshot


class CompareResponse(BaseModel):
    delta: ProfileCompareDelta
    anomalies: list[AnomalyItem] = Field(default_factory=list)
