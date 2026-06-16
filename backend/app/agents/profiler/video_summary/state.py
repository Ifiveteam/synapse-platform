from __future__ import annotations

import uuid
from typing import TypedDict


class WatchInput(TypedDict):
    """LLM 입력용으로 추린 user_video_watch 필드."""

    watch_id: uuid.UUID
    title: str | None
    channel: str
    description: str | None
    transcript: str | None
    tags: list | None
    category: str | None


class AnalyzedVideo(TypedDict):
    """영상 1건의 분석 결과 (임베딩 전/후 공용)."""

    watch_id: uuid.UUID
    summary_kr: str
    tones: list[str]
    intents: list[str]
    value_signals: list[str]
    embedding_text: str
    embedding: list[float] | None  # embed 노드에서 채움


class VideoSummaryState(TypedDict):
    # 입력
    user_id: uuid.UUID
    limit: int | None

    # 단계별 결과
    watches: list[WatchInput]
    analyzed: list[AnalyzedVideo]

    # 저장 결과
    saved_count: int | None
    skipped_count: int | None

    # 에러 게이트
    error: str | None

    # 실행 메타
    started_at: float | None
    run_log: str | None
