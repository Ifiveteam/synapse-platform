"""비교 분석 LLM structured output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompareNarrativeOutput(BaseModel):
    """두 프로필 스냅샷 비교 해석 (LLM 산출)."""

    headline: str = Field(description="한 줄 핵심 변화 요약")
    summary_text: str = Field(description="3~5문장 전체 변화 서술")
    key_shifts: list[str] = Field(
        default_factory=list,
        description="핵심 변화 3~5개 (짧은 문장)",
    )
    stable_traits: list[str] = Field(
        default_factory=list,
        description="유지·안정된 성향",
    )
    viewing_pattern_note: str = Field(
        description="시청 습관(편중·다양성·쇼츠) 변화 한 단락"
    )
