"""Profiler LLM structured output — 필드명은 user_profile_history 컬럼과 동일."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ValuesTemperamentOutput(BaseModel):
    """1단계: Schwartz 가치관 10 + TCI 기질 3."""

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


class BehaviorSpiderOutput(BaseModel):
    """2단계: 1단계 점수로부터 도출하는 행동 스파이더 8."""

    exploration: float = Field(ge=0, le=100)
    analytical: float = Field(ge=0, le=100)
    creativity: float = Field(ge=0, le=100)
    execution: float = Field(ge=0, le=100)
    achievement_drive: float = Field(ge=0, le=100)
    autonomy: float = Field(ge=0, le=100)
    sociality: float = Field(ge=0, le=100)
    sensitivity: float = Field(ge=0, le=100)


class ProfileScoresOutput(BaseModel):
    """user_profile_history 점수 컬럼."""

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
    exploration: float = Field(ge=0, le=100)
    analytical: float = Field(ge=0, le=100)
    creativity: float = Field(ge=0, le=100)
    execution: float = Field(ge=0, le=100)
    achievement_drive: float = Field(ge=0, le=100)
    autonomy: float = Field(ge=0, le=100)
    sociality: float = Field(ge=0, le=100)
    sensitivity: float = Field(ge=0, le=100)


class ProfileInsightOutput(BaseModel):
    """user_profile_history 해석 컬럼 (LLM 산출)."""

    summary_text: str
    persona_label: str | None = None
    behavior_reasoning: str | None = None
    dominant_traits: list[str] = Field(default_factory=list)
    tone_of_user: str | None = None
