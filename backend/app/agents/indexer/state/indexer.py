import uuid
from typing import TypedDict


class VideoItem(TypedDict, total=False):
    title: str
    channel: str
    channel_url: str
    url: str
    watched_at: str
    category: str
    keywords: list[str]
    duration: int
    is_shorts: bool
    description: str
    thumbnail_url: str
    transcript: str


class IndexerState(TypedDict):
    # 입력
    json_path: str

    # 파싱 결과
    raw_data: list[dict]

    # 전처리 결과 (2개월 전체)
    cleaned_data: list[VideoItem]
    filtered_count: int | None
    analysis_start: str | None
    analysis_end: str | None

    # 샘플 (카테고리×타입별 최신 5개)
    sampled_data: list[VideoItem]
    sample_count: int | None

    # 에러
    error: str | None

    # DB 저장 결과
    saved_count: int | None

    limit: int | None
    reindex: bool | None

    # 실행 메타
    started_at: float | None
    run_log: str | None
    user_id: uuid.UUID | None


class ExtensionState(TypedDict):
    videos: list[dict]
    cleaned_data: list[VideoItem]
    error: str | None
    saved_count: int | None
