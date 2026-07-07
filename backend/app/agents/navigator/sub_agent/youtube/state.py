"""YouTube 재생목록 서브에이전트 LangGraph 상태."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import NotRequired, TypedDict

from app.agents.navigator.schemas import Playlist, PlaylistItem
from app.agents.navigator.sub_agent.youtube.schemas import ChannelRef, WatchGrounding


class PlaylistState(TypedDict):
    user_id: uuid.UUID
    # 이상향 페르소나 (8축 아님, 13축 + 라벨/근거)
    persona_label: str
    values13: dict[str, float]
    ideal_type: str
    reasoning: str

    # 도메인 신호 (B-1): 현재 관심 분포 + 넓힐 목표 도메인 + 목표 성향
    current_interest: NotRequired[dict[str, float]]
    raise_domains: NotRequired[list[str]]
    target_disposition: NotRequired[dict[str, float]]
    taste_keywords: NotRequired[list[str]]  # 대화에서 뽑은 구체 관심 키워드

    # 시청기록 근거 / watched (discover에서 store로 1회 로드)
    grounding: NotRequired[WatchGrounding]
    watched: NotRequired[set[str]]

    # 작업 누적
    queries: NotRequired[list[str]]
    tried_queries: NotRequired[list[str]]
    found_channels: NotRequired[list[ChannelRef]]
    picked_channels: NotRequired[list[ChannelRef]]
    candidates: NotRequired[list[PlaylistItem]]

    # 자기교정
    attempts: NotRequired[int]
    decision: NotRequired[str]

    result: NotRequired[Playlist | None]


@dataclass(frozen=True, slots=True)
class PlaylistBuild:
    """run_playlist 결과 — 보여줄 목록 + 여분(저수지) + 발굴 채널."""

    playlist: Playlist
    reservoir: list[PlaylistItem] = field(default_factory=list)
    channels: list[ChannelRef] = field(default_factory=list)
