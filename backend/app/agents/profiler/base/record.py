from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["watch", "search", "scrap"]


class IndexedRecord(BaseModel):
    id: str
    source_type: SourceType
    title: str | None = None
    url: str | None = None
    channel: str | None = None
    query: str | None = None
    duration_sec: int | None = None
    is_shorts: bool = False
    recorded_at: datetime | None = None
    vector_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class IndexedRecordsBundle(BaseModel):
    user_id: str
    indexed_at: datetime | None = None
    source: str = "portability"
    records: list[IndexedRecord] = Field(default_factory=list)
