from __future__ import annotations

import uuid
from typing import TypedDict


class CatalogInput(TypedDict):
    """LLM 입력용 catalog 한 건."""

    catalog_id: uuid.UUID
    user_id: uuid.UUID
    url: str | None
    title: str | None
    channel: str
    description: str | None
    transcript: str | None
    tags: list | None
    youtube_category_id: str | None
    thumbnail_url: str | None


class AnalyzedVideo(TypedDict, total=False):
    catalog_id: uuid.UUID
    user_id: uuid.UUID
    summary_kr: str
    tones: list[str]
    intents: list[str]
    value_signals: list[str]
    transcript: str | None
    embedding_text: str
    embedding: list[float] | None


class VideoSummaryState(TypedDict):
    user_id: uuid.UUID
    limit: int | None

    catalogs: list[CatalogInput]
    analyzed: list[AnalyzedVideo]

    saved_count: int | None
    skipped_count: int | None
    error: str | None

    started_at: float | None
    run_log: str | None
