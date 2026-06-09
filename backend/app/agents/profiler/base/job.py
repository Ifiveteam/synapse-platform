from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

DEFAULT_FROM_ADDRESS = "synapse@ifive.site"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InAppChannel(BaseModel):
    delivered: bool = True


class EmailChannel(BaseModel):
    attempted: bool = False
    sent: bool = False
    from_address: str = DEFAULT_FROM_ADDRESS
    recipient_masked: str = ""
    error: str | None = None


class NotificationChannels(BaseModel):
    in_app: InAppChannel = Field(default_factory=InAppChannel)
    email: EmailChannel = Field(default_factory=EmailChannel)


class NotificationPayload(BaseModel):
    type: str
    message: str = ""
    channels: NotificationChannels = Field(default_factory=NotificationChannels)


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
