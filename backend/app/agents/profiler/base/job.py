from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PersonaInfo(BaseModel):
    id: str
    label: str
    description: str


class BehaviorEvent(BaseModel):
    event_type: str
    url: str | None = None
    title: str | None = None
    duration_ms: int | None = None
    recorded_at: datetime | None = None


class BehaviorEventSummary(BaseModel):
    total_events: int = 0
    total_dwell_ms: int = 0
    click_count: int = 0
