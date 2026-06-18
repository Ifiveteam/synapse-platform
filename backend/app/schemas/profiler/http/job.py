"""프로파일러 job HTTP 응답."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.profiler.http.snapshot import DbProfileResponse
from app.schemas.profiler.job import JobStatus
from app.services.notification import NotificationPayload


class AnalyzeResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING


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
