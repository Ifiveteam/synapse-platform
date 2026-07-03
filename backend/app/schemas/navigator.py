"""Navigator API Pydantic 스키마 (HTTP 경계)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IdealTypeStr = Literal["OPPOSITE", "DEEPEN", "BALANCE", "CUSTOM"]


class AxisScores8(BaseModel):
    """Synapse 행동 8축 점수 (0~100)."""

    exploration: float = Field(ge=0, le=100)
    analytical: float = Field(ge=0, le=100)
    creativity: float = Field(ge=0, le=100)
    execution: float = Field(ge=0, le=100)
    achievement_drive: float = Field(ge=0, le=100)
    autonomy: float = Field(ge=0, le=100)
    sociality: float = Field(ge=0, le=100)
    sensitivity: float = Field(ge=0, le=100)


class AxisScores13(BaseModel):
    """가치관 10축 + 기질 3축 점수 (0~100). 이상향 설계 축."""

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


class DispositionPair(BaseModel):
    """성향 6축 한 개 — 현재(초상) vs 목표(이상향)."""

    key: str
    label_ko: str
    current: float
    target: float


class DomainPair(BaseModel):
    """관심 도메인 한 개 — 현재(초상) vs 목표(이상향)."""

    domain: str
    current: float
    target: float


class ProposalItem(BaseModel):
    ideal_type: IdealTypeStr
    scores: AxisScores8  # 폴드용(행동 8축)
    values_temperament: AxisScores13  # 폴드용(가치관·기질 13축)
    disposition: list[DispositionPair] = Field(default_factory=list)  # 성향 현재→목표
    interest: list[DomainPair] = Field(default_factory=list)  # 도메인 현재→목표
    persona_label: str = ""
    reasoning: str = ""


class ProposalsResponse(BaseModel):
    proposals: list[ProposalItem]  # OPPOSITE / DEEPEN / BALANCE 3종


class NavigatorChatRequest(BaseModel):
    message: str = Field(
        default="", description="사용자 메시지 (force_finalize면 비워도 됨)"
    )
    session_id: str | None = None
    working_values: AxisScores13 | None = Field(
        default=None, description="클라이언트가 들고 있는 이상향 13축 상태 (설계 원본)"
    )
    # 인터뷰 중 조율된 목표(성향·도메인). 매 턴 클라가 에코해 러닝 상태를 이어감.
    working_disposition: dict[str, float] | None = None
    working_interest: dict[str, float] | None = None
    ideal_type: IdealTypeStr | None = None
    # 확정 버튼 — 턴 캡 무시하고 즉시 마무리
    force_finalize: bool = False


class ConfirmIdealRequest(BaseModel):
    ideal_type: IdealTypeStr
    scores: AxisScores8
    values_temperament: AxisScores13 | None = None
    # 확정할 이상향의 목표 성향·도메인 (선택한 제안/조율 결과). 없으면 저장 안 함.
    target_disposition: dict[str, float] | None = None
    target_interest: dict[str, float] | None = None
    persona_label: str = ""
    reasoning: str = ""
    source_profile_history_id: str | None = None


class IdealResponse(BaseModel):
    id: str
    ideal_type: IdealTypeStr
    scores: AxisScores8
    values_temperament: AxisScores13 | None = None
    # 목표 신호(저장값). 현재값과의 대비는 comparison 엔드포인트에서.
    target_disposition: dict[str, float] | None = None
    target_interest: dict[str, float] | None = None
    persona_label: str = ""
    reasoning: str = ""
    is_active: bool = False
    updated_at: datetime


class AxisGapItem(BaseModel):
    axis: str
    label_ko: str
    current: float
    ideal: float
    gap: float


class ComparisonResponse(BaseModel):
    current: AxisScores8
    ideal: AxisScores8
    gaps: list[AxisGapItem]
    total_gap: float
    # 가치관·기질 13축 (현재=스냅샷, 이상향=저장값). 둘 중 하나라도 없으면 null.
    current_vt: AxisScores13 | None = None
    ideal_vt: AxisScores13 | None = None
    # 주 표시 축: 성향 6축·관심 도메인 현재(스냅샷 초상)→목표(이상향)
    disposition: list[DispositionPair] = Field(default_factory=list)
    interest: list[DomainPair] = Field(default_factory=list)


class GuideStepItem(BaseModel):
    axis: str
    label_ko: str
    kind: Literal["deepen", "expand"] = "deepen"
    title: str
    detail: str
    priority: int


class GuideResponse(BaseModel):
    summary: str
    steps: list[GuideStepItem]
    generated_at: datetime | None = None
    stale: bool = False  # 생성 후 시청기록이 늘었으면 True (재생성 권장)


class NavigatorChatMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


# ── 재생목록 (PLAN_youtube_playlist.md) ──────────────────────────


class PlaylistItemResponse(BaseModel):
    video_id: str
    title: str
    channel: str = ""
    channel_id: str = ""
    thumbnail_url: str = ""
    url: str
    reason: str = ""


PlaylistStatus = Literal["pending", "ready", "failed"]


class PlaylistResponse(BaseModel):
    id: str
    ideal_id: str
    title: str = ""
    summary: str = ""
    items: list[PlaylistItemResponse]
    status: PlaylistStatus = "ready"
    youtube_playlist_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PlaylistSummary(BaseModel):
    """목록용 경량 응답."""

    id: str
    title: str = ""
    item_count: int = 0
    status: PlaylistStatus = "ready"
    youtube_playlist_id: str | None = None
    created_at: datetime


class RenamePlaylistRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class RefreshItemRequest(BaseModel):
    video_id: str = Field(min_length=1, description="교체할 현재 영상 video_id")


class PlaylistChatRequest(BaseModel):
    message: str = Field(min_length=1, description="재생목록 수정 요청 (자연어)")


class SavePlaylistResponse(BaseModel):
    youtube_playlist_id: str
    playlist_url: str
    added_count: int
    needs_reconsent: bool = False
