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


class ProposalItem(BaseModel):
    ideal_type: IdealTypeStr
    scores: AxisScores8
    values_temperament: AxisScores13
    persona_label: str = ""
    reasoning: str = ""


class ProposalsResponse(BaseModel):
    proposals: list[ProposalItem]  # OPPOSITE / DEEPEN / BALANCE 3종


class NavigatorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="사용자 메시지")
    session_id: str | None = None
    working_values: AxisScores13 | None = Field(
        default=None, description="클라이언트가 들고 있는 이상향 13축 상태 (설계 원본)"
    )
    ideal_type: IdealTypeStr | None = None


class ConfirmIdealRequest(BaseModel):
    ideal_type: IdealTypeStr
    scores: AxisScores8
    values_temperament: AxisScores13 | None = None
    persona_label: str = ""
    reasoning: str = ""
    source_profile_history_id: str | None = None


class IdealResponse(BaseModel):
    id: str
    ideal_type: IdealTypeStr
    scores: AxisScores8
    values_temperament: AxisScores13 | None = None
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


class GuideStepItem(BaseModel):
    axis: str
    label_ko: str
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
