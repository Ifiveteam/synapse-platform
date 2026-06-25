"""YouTube 재생목록 서브에이전트 전용 모델 (youtube 안에서만 사용).

서브 밖으로 나가는 결과 모델(PlaylistItem·Playlist)은 root schemas.py에 둔다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── 외부 IO raw shape (client.py가 API·RSS 응답에서 생성) ────────


class ChannelRef(BaseModel):
    """검색으로 찾은 실재 채널."""

    channel_id: str
    title: str
    description: str = ""


class YoutubeVideo(BaseModel):
    """채널 RSS에서 수집한 영상 후보."""

    video_id: str
    title: str
    channel: str = ""
    channel_id: str = ""
    thumbnail_url: str = ""
    published_at: str = ""

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


# ── store(시청기록 Port) 반환 ───────────────────────────────────


class WatchGrounding(BaseModel):
    """추천 근거가 되는 사용자 시청 기록 요약."""

    categories: list[str] = Field(default_factory=list)  # 상위 카테고리(라벨/id)
    channels: list[str] = Field(default_factory=list)  # 상위 채널명
    sample_titles: list[str] = Field(default_factory=list)  # 대표 시청영상 제목


# ── Gemini Structured Output (노드 전용) ────────────────────────


class QuerySpec(BaseModel):
    """discover 노드 — 이상향+시청기록 → 채널 검색어 (Structured Output)."""

    queries: list[str] = Field(
        description="페르소나에 맞는 YouTube 채널 검색어 1~2개 (한국어)"
    )


class ChannelPick(BaseModel):
    """pick 노드 — 실재 채널 후보 중 선택 (인덱스, id 환각 방지)."""

    indices: list[int] = Field(description="후보 채널 목록의 0-기반 인덱스")


class CuratedVideo(BaseModel):
    index: int = Field(description="후보 영상 목록의 0-기반 인덱스")
    reason: str = Field(default="", description="이 영상을 고른 한 줄 이유 (한국어)")


class PlaylistCuration(BaseModel):
    """curate 노드 — 후보 영상 중 선택 + 이유 (인덱스만, id 출력 금지)."""

    summary: str = Field(default="", description="재생목록 총평 (한국어 1~2문장)")
    picks: list[CuratedVideo] = Field(default_factory=list)


class EditSpec(BaseModel):
    """채팅 편집 interpret — 사용자 요청 해석 (Structured Output)."""

    scope: Literal["reshuffle", "swap", "add_theme"] = Field(
        description="reshuffle=풀에서 재구성, swap=특정 영상 교체, add_theme=새 주제 검색"
    )
    target_indices: list[int] = Field(
        default_factory=list,
        description="교체/제거할 현재 영상의 0-기반 인덱스 (현재 목록 번호). 보통 1~2개",
    )
    new_query: str = Field(
        default="", description="add_theme일 때 새로 검색할 채널 검색어"
    )
    note: str = Field(default="", description="편집 요약 (status 이벤트용 한 줄)")
