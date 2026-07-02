import uuid
from typing import NotRequired, TypedDict


class VideoItem(TypedDict, total=False):
    platform: str
    title: str
    channel: str
    channel_url: str
    url: str
    watched_at: str
    watch_count: int
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
    cleaned_data: list[VideoItem]  # diff 이후 = 신규 영상(enrich/embed 대상)
    filtered_count: int | None
    analysis_start: str | None
    analysis_end: str | None
    error: str | None
    saved_count: int | None
    user_id: uuid.UUID | None
    # 배치: 이 파일의 소스 id (저장 시 소속 짝 기록용). 스크립트 실행 등에선 없음.
    analysis_source_id: NotRequired[str | None]
    # 증분 인덱싱
    existing_items: NotRequired[list[VideoItem]]  # 기존 = watched_at·watch_count만 갱신
    skipped_existing: NotRequired[int]
    touched_count: NotRequired[int]
    # 구독정보 (ZIP 전용) — 파일 있을 때만 전체 교체
    subscriptions: NotRequired[list[dict]]
    subscription_file_found: NotRequired[bool]
    subscription_saved: NotRequired[int]
