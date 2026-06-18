from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VideoSemanticAnalysis(BaseModel):
    """영상 1건의 의미분석 (Gemini structured output)."""

    summary_kr: str = Field(
        ...,
        description=(
            "유저 성향 추론용 시맨틱 브리프. 3~5문장(200~400자): "
            "주제·도메인 → 시청 동기 → 인지·소비 방식 → 감정·톤 맥락 → 가치·태도 순. "
            "라벨(tones/intents/value_signals)과 같은 단어 반복 금지."
        ),
    )
    tones: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="영상의 톤/분위기 라벨 정확히 3개",
    )
    intents: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="영상의 의도 라벨 정확히 3개",
    )
    value_signals: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="영상이 담은 가치 신호 라벨 정확히 3개",
    )

    @field_validator("tones", "intents", "value_signals")
    @classmethod
    def _exactly_three(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) >= 3:
            return cleaned[:3]
        return cleaned + ["미상"] * (3 - len(cleaned))
