from typing import TypedDict


class VideoItem(TypedDict):
    title: str
    channel: str
    channel_url: str
    url: str
    watched_at: str
    category: str
    embedding: list[float]
    keywords: list[str]
    duration: int
    is_shorts: bool


class IndexerState(TypedDict):
    # 입력
    json_path: str

    # 파싱 결과
    raw_data: list[dict]

    # 전처리 결과
    cleaned_data: list[VideoItem]
    filtered_count: int | None  # 노이즈 제거 후, limit 적용 전 개수

    # 에러
    error: str | None

    # DB 저장 결과
    saved_count: int | None

    limit: int | None


class ExtensionState(TypedDict):
    videos: list[dict]
    cleaned_data: list[VideoItem]
    error: str | None
    saved_count: int | None
