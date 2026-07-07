"""어그리게이터 도메인 분포 Pydantic 스키마."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, RootModel, field_validator

from app.models.trend_domain import TrendDomain

UNMAPPED_KEY: Literal["UNMAPPED"] = "UNMAPPED"
DomainScoreMap = dict[TrendDomain, float]
_WEIGHT_SUM_TOLERANCE = 0.02
_MIN_TREND_KEYWORDS = 3
_MAX_TREND_KEYWORDS = 5


class TrendDomainWeight(BaseModel):
    domain: TrendDomain
    weight: float = Field(ge=0.0, le=1.0)


class TrendDomainLLMOutput(BaseModel):
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall mapping confidence between 0 and 1",
    )
    domains: list[TrendDomainWeight] = Field(min_length=1, max_length=6)
    trend_keywords: list[str] = Field(
        min_length=_MIN_TREND_KEYWORDS,
        max_length=_MAX_TREND_KEYWORDS,
        description=(
            "Standardized trend entities (3-5). Dedupe synonyms; "
            "prefer brands, products, technologies, issues."
        ),
    )

    @field_validator("domains")
    @classmethod
    def _weights_positive(
        cls, domains: list[TrendDomainWeight]
    ) -> list[TrendDomainWeight]:
        if not domains:
            msg = "domains must not be empty"
            raise ValueError(msg)
        return domains

    @field_validator("trend_keywords")
    @classmethod
    def _normalize_keyword_strings(cls, keywords: list[str]) -> list[str]:
        cleaned = [kw.strip() for kw in keywords if kw and kw.strip()]
        if len(cleaned) < _MIN_TREND_KEYWORDS:
            msg = f"trend_keywords must contain at least {_MIN_TREND_KEYWORDS} items"
            raise ValueError(msg)
        return cleaned[:_MAX_TREND_KEYWORDS]


class DomainDistributionSchema(RootModel[dict[TrendDomain, float]]):
    """6대 TrendDomain 점수 분포 — 합계 1.0(비어 있으면 UNMAPPED)."""

    root: dict[TrendDomain, float]

    @property
    def is_unmapped(self) -> bool:
        return len(self.root) == 0

    @property
    def scores(self) -> DomainScoreMap:
        return dict(self.root)

    @field_validator("root")
    @classmethod
    def _validate_weight_sum(
        cls,
        value: dict[TrendDomain, float],
    ) -> dict[TrendDomain, float]:
        if not value:
            return {}
        total = sum(value.values())
        if total <= 0:
            return {}
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            return {domain: weight / total for domain, weight in value.items()}
        return value

    @classmethod
    def empty(cls) -> DomainDistributionSchema:
        return cls({})

    @classmethod
    def from_scores(cls, scores: dict[TrendDomain, float]) -> DomainDistributionSchema:
        if not scores:
            return cls.empty()
        total = sum(scores.values())
        if total <= 0:
            return cls.empty()
        normalized = {domain: weight / total for domain, weight in scores.items()}
        return cls(normalized)

    @classmethod
    def single(cls, domain: TrendDomain) -> DomainDistributionSchema:
        return cls({domain: 1.0})

    @classmethod
    def unmapped_explicit(cls) -> dict[Literal["UNMAPPED"], float]:
        return {UNMAPPED_KEY: 1.0}


@dataclass(frozen=True)
class TrendMappingResult:
    """도메인 분포 + LLM/숏컷이 정제한 트렌드 키워드."""

    distribution: DomainDistributionSchema
    trend_keywords: list[str]

    @property
    def scores(self) -> DomainScoreMap:
        return self.distribution.scores

    @classmethod
    def unmapped(cls) -> TrendMappingResult:
        return cls(distribution=DomainDistributionSchema.empty(), trend_keywords=[])
