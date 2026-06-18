import uuid
from typing import TypedDict


class VideoItem(TypedDict, total=False):
    platform: str
    title: str
    channel: str
    channel_url: str
    url: str
    watched_at: str
    youtube_category_id: str
    duration_sec: int
    is_shorts: bool
    description: str
    tags: list[str]
    thumbnail_url: str
    embedding_text: str | None
    embedding: list[float] | None


class IndexerState(TypedDict):
    json_path: str
    raw_data: list[dict]
    cleaned_data: list[VideoItem]
    filtered_count: int | None
    analysis_start: str | None
    analysis_end: str | None
    error: str | None
    saved_count: int | None
    user_id: uuid.UUID | None
