from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VideoSemanticAnalysis(BaseModel):
    """영상 1건의 의미분석 (Gemini structured output)."""

    summary_kr: str = Field(
        ...,
        description="영상 내용을 1~2문장으로 요약한 자연스러운 한국어 문장",
    )
    tones: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description='영상의 톤/분위기를 나타내는 짧은 한국어 라벨 정확히 3개. 예: ["진지함","유머","차분함"]',
    )
    intents: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description='영상의 의도를 나타내는 짧은 한국어 라벨 정확히 3개. 예: ["정보전달","설득","공감"]',
    )
    value_signals: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description='영상이 담은 가치 신호를 나타내는 짧은 한국어 라벨 정확히 3개. 예: ["성취","재미","안정"]',
    )

    @field_validator("tones", "intents", "value_signals")
    @classmethod
    def _exactly_three(cls, v: list[str]) -> list[str]:
        """모델이 길이를 어겨도 파이프라인이 죽지 않도록 정확히 3개로 정규화."""
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) >= 3:
            return cleaned[:3]
        return cleaned + ["미상"] * (3 - len(cleaned))
