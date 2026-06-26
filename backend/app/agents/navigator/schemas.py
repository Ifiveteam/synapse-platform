"""Navigator 에이전트 내부 도메인 Pydantic + Gemini Structured Output 스키마.

HTTP 경계 DTO는 ``app/schemas/navigator.py``에 따로 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.navigator.constants import (
    BEHAVIOR_AXES,
    VALUES_TEMPERAMENT_AXES,
)

StreamEventType = Literal["status", "token", "ideal", "playlist"]


class IdealType(StrEnum):
    OPPOSITE = "OPPOSITE"  # 반대형 — 강점↓ 약점↑ (정체성 반전·버블 탈출)
    DEEPEN = "DEEPEN"  # 강점심화형 — 강점↑ (전문화)
    BALANCE = "BALANCE"  # 균형형(약점보완) — 강점 유지 + 약점↑
    CUSTOM = "CUSTOM"  # 챗봇으로 조율한 사용자 맞춤


class IdealRadar(BaseModel):
    """8축 이상향 타깃 + 근거. Gemini Structured Output 겸 내부 계약."""

    exploration: float = Field(ge=0, le=100)
    analytical: float = Field(ge=0, le=100)
    creativity: float = Field(ge=0, le=100)
    execution: float = Field(ge=0, le=100)
    achievement_drive: float = Field(ge=0, le=100)
    autonomy: float = Field(ge=0, le=100)
    sociality: float = Field(ge=0, le=100)
    sensitivity: float = Field(ge=0, le=100)
    persona_label: str = Field(
        default="",
        description="이 이상향을 한마디로 부르는 페르소나 명칭 (한국어, 예: '창의적인 탐색가')",
    )
    reasoning: str = Field(
        default="", description="이 이상향을 제안한 근거 (한국어 2~4문장)"
    )

    def scores(self) -> dict[str, float]:
        return {axis: float(getattr(self, axis)) for axis in BEHAVIOR_AXES}

    @classmethod
    def from_scores(
        cls, scores: dict[str, float], reasoning: str = "", persona_label: str = ""
    ) -> "IdealRadar":
        return cls(
            **{axis: float(scores.get(axis, 0.0)) for axis in BEHAVIOR_AXES},
            persona_label=persona_label,
            reasoning=reasoning,
        )


class IdealValuesDesign(BaseModel):
    """이상향을 13축(가치관10+기질3)으로 설계한 LLM 출력. 8축은 여기서 파생한다."""

    # 가치관 10축
    self_direction: float = Field(ge=0, le=100)
    stimulation: float = Field(ge=0, le=100)
    achievement: float = Field(ge=0, le=100)
    power: float = Field(ge=0, le=100)
    security: float = Field(ge=0, le=100)
    benevolence: float = Field(ge=0, le=100)
    universalism: float = Field(ge=0, le=100)
    hedonism: float = Field(ge=0, le=100)
    conformity: float = Field(ge=0, le=100)
    tradition: float = Field(ge=0, le=100)
    # 기질 3축
    novelty_seeking: float = Field(ge=0, le=100)
    persistence: float = Field(ge=0, le=100)
    self_transcendence: float = Field(ge=0, le=100)

    persona_label: str = Field(
        default="",
        description="이 이상향을 한마디로 부르는 페르소나 명칭 (한국어, 예: '창의적인 탐색가')",
    )
    reasoning: str = Field(
        default="", description="이 방향을 설계한 근거 (한국어 2~4문장)"
    )

    def values(self) -> dict[str, float]:
        return {axis: float(getattr(self, axis)) for axis in VALUES_TEMPERAMENT_AXES}


@dataclass(frozen=True, slots=True)
class ProposedIdeal:
    """제안된 이상향 한 건 — 13축 설계 + 파생 8축 + 페르소나/근거."""

    ideal_type: IdealType
    scores8: dict[str, float] = field(default_factory=dict)
    values13: dict[str, float] = field(default_factory=dict)
    persona_label: str = ""
    reasoning: str = ""


class IdealAdjustment(BaseModel):
    """interpret 노드 — 유저 턴이 이상향을 어떻게 바꾸는지 (Structured Output, 13축 기준)."""

    updated_design: IdealValuesDesign = Field(description="조정 후 13축 이상향 전체")
    changed: bool = Field(description="유저가 실제로 변경을 요청했는지")
    note: str = Field(default="", description="조정 요약 (status 이벤트용 한 줄)")


class AxisGap(BaseModel):
    axis: str
    label_ko: str
    current: float
    ideal: float
    gap: float  # ideal - current (부호 있음)


class RadarComparison(BaseModel):
    gaps: list[AxisGap]
    gap_by_axis: dict[str, float]
    total_gap: float  # abs(gap) 합계


class GuideStep(BaseModel):
    axis: str = Field(description="대상 축 key (예: creativity)")
    label_ko: str = Field(default="", description="축 한글 라벨")
    title: str = Field(description="행동 제목")
    detail: str = Field(description="구체적 실행 방법")
    priority: int = Field(default=1, description="우선순위 (1=가장 높음)")


class Guide(BaseModel):
    summary: str = Field(description="가이드 총평 (한국어)")
    steps: list[GuideStep] = Field(default_factory=list)


# ── YouTube 재생목록 (PLAN_youtube_playlist.md) ──────────────────


class PlaylistItem(BaseModel):
    """재생목록 영상 1개. video_id는 코드(search/RSS)가 소유한 실재값."""

    video_id: str
    title: str
    channel: str = ""
    channel_id: str = ""
    thumbnail_url: str = ""
    reason: str = Field(default="", description="이 영상이 이상향에 맞는 한 줄 이유")

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


class Playlist(BaseModel):
    summary: str = Field(default="", description="재생목록 총평 (한국어)")
    items: list[PlaylistItem] = Field(default_factory=list)


# youtube 노드 전용 Structured Output(QuerySpec·ChannelPick·PlaylistCuration·EditSpec)은
# sub_agent/youtube/schemas.py 로 이동.


@dataclass(frozen=True, slots=True)
class NavigatorStreamEvent:
    event: StreamEventType
    content: str
