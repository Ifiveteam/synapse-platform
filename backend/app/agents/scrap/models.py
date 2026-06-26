"""Scrap Gemini Structured Output 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScrapClassificationResult(BaseModel):
    """스크랩 본문·대화 맥락에 대한 요약·분류 결과."""

    summary: str = Field(
        ...,
        description="핵심을 담은 한 줄 요약 (한국어, 120자 이내)",
    )
    category: str = Field(
        ...,
        description="주제 카테고리 (한국어, 예: 기술/AI, 비즈니스, 라이프스타일)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="핵심 키워드 태그 3~7개 (한국어 또는 원문 유지)",
    )
