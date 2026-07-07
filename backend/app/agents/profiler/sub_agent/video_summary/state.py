from __future__ import annotations

import uuid
from typing import NotRequired, TypedDict


class CatalogInput(TypedDict):
    """LLM 입력용 catalog 한 건."""

    catalog_id: uuid.UUID
    user_id: uuid.UUID
    url: str | None
    title: str | None
    channel: str
    description: str | None
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
    embedding_text: str
    embedding: list[float] | None


class VideoSummaryState(TypedDict):
    user_id: uuid.UUID
    limit: int | None
    # 배치 스코프: 메인 파이프라인에서 그 배치 소스들만 분석 대상으로 삼는다.
    analysis_source_ids: NotRequired[list[str] | None]

    catalogs: list[CatalogInput]
    analyzed: list[AnalyzedVideo]

    saved_count: int | None
    skipped_count: int | None
    error: str | None

    started_at: float | None
    run_log: str | None
