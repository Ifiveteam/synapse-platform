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
    DISPOSITION_AXES,
    VALUES_TEMPERAMENT_AXES,
)

StreamEventType = Literal["status", "token", "ideal", "playlist", "complete"]


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


class DispositionScores(BaseModel):
    """성향 6축(0~100) — portrait disposition과 동일 축. 이상향 목표값."""

    immersion: float = Field(ge=0, le=100, description="몰입도")
    exploration: float = Field(ge=0, le=100, description="탐험성(콘텐츠 다양성)")
    fandom: float = Field(ge=0, le=100, description="팬심")
    trend: float = Field(ge=0, le=100, description="트렌드민감")
    info: float = Field(ge=0, le=100, description="정보추구")
    emotion: float = Field(ge=0, le=100, description="감성지향")

    def as_dict(self) -> dict[str, float]:
        return {axis: float(getattr(self, axis)) for axis in DISPOSITION_AXES}


class InterestTarget(BaseModel):
    """이상향의 관심 도메인 목표값 한 건."""

    domain: str = Field(description="관심 도메인명 (제공된 9개 중 하나 그대로)")
    target: float = Field(ge=0, le=100, description="이상향에서의 목표 관심도 0~100")


class IdealValuesDesign(BaseModel):
    """이상향 LLM 출력 — 목표 성향 6축 + 목표 관심 도메인(주) + 13축(내부 파생용)."""

    # ── 주 출력: 화면·저장·재생목록이 쓰는 목표 ──
    target_disposition: DispositionScores = Field(
        description="이상향의 목표 성향 6축(현재와 크게 벌릴 것)"
    )
    target_interest: list[InterestTarget] = Field(
        default_factory=list,
        description="이상향의 목표 관심 도메인값 — 제공된 9개 도메인 각각",
    )

    # ── 내부 파생용: 가치관 10축 + 기질 3축 (8축은 여기서 파생, 화면은 폴드) ──
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
    """제안된 이상향 한 건 — 목표 성향·도메인(주) + 13축 설계 + 파생 8축 + 페르소나/근거."""

    ideal_type: IdealType
    scores8: dict[str, float] = field(default_factory=dict)
    values13: dict[str, float] = field(default_factory=dict)
    target_disposition: dict[str, float] = field(default_factory=dict)
    target_interest: dict[str, float] = field(default_factory=dict)
    persona_label: str = ""
    reasoning: str = ""


class IdealAdjustment(BaseModel):
    """interpret 노드 — 유저 턴이 이상향을 어떻게 바꾸는지 (Structured Output, 13축 기준)."""

    updated_design: IdealValuesDesign = Field(description="조정 후 13축 이상향 전체")
    changed: bool = Field(description="유저가 실제로 변경을 요청했는지")
    note: str = Field(default="", description="조정 요약 (status 이벤트용 한 줄)")


class InterviewTurn(BaseModel):
    """인터뷰 한 턴 — 취향 대화로 갱신된 이상향 설계 + 대화 제어(종료 판단)."""

    design: IdealValuesDesign = Field(
        description="지금까지의 취향을 반영해 갱신한 이상향 전체(13축 + 목표 성향·도메인)"
    )
    sufficient: bool = Field(
        description="이상향을 확정할 만큼 취향을 충분히 파악했는가"
    )
    user_wants_finalize: bool = Field(
        description="사용자가 이번 발화에서 '이제 끝/이걸로 확정' 의도를 보였는가"
    )
    taste_notes: str = Field(
        default="", description="지금까지 파악한 사용자 취향 요약(누적, 한국어)"
    )
    missing: list[str] = Field(
        default_factory=list, description="아직 불명확해 더 물어보면 좋을 측면"
    )


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
    axis: str = Field(
        description="대상 축 — 심화면 성향키(immersion 등), 확장이면 도메인명(지식·교육 등)"
    )
    label_ko: str = Field(default="", description="축 한글 라벨")
    kind: Literal["deepen", "expand"] = Field(
        default="deepen",
        description="deepen=기존 취향 심화(시청 근거) / expand=새 도메인 확장",
    )
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
