from __future__ import annotations

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
