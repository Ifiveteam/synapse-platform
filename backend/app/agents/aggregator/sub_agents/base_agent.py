"""서브 에이전트 추상 부모 — BaseTrendAgent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.agents.aggregator.schemas import (
    _MAX_TREND_KEYWORDS,
    DomainDistributionSchema,
    DomainScoreMap,
    TrendDomainLLMOutput,
    TrendDomainWeight,
    TrendMappingResult,
)
from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger, LayerName
from app.agents.shared.gemini import GEMINI_MODEL, invoke_structured_safe
from app.models.trend_domain import TrendDomain

DEFAULT_LLM_MODEL = GEMINI_MODEL
CONFIDENCE_THRESHOLD = 0.55
AMBIGUITY_TOP_GAP = 0.15


class BaseTrendAgent(ABC):
    """모든 도메인 분류 서브 에이전트의 공통 인터페이스."""

    layer: LayerName

    def __init__(self, agg_logger: AggregatorLogger | None = None) -> None:
        self._log = agg_logger or AggregatorLogger()

    @abstractmethod
    async def map_domain(self, **kwargs: Any) -> TrendMappingResult:
        """입력 페이로드를 6대 TrendDomain 분포 + 트렌드 키워드로 변환한다."""

    @staticmethod
    def normalize_scores(scores: dict[TrendDomain, float]) -> DomainScoreMap:
        return DomainDistributionSchema.from_scores(scores).scores

    @staticmethod
    def normalize_trend_keywords(keywords: list[str] | None) -> list[str]:
        """키워드 중복·공백 제거 — 최대 5개."""
        if not keywords:
            return []
        seen: set[str] = set()
        normalized: list[str] = []
        for keyword in keywords:
            cleaned = keyword.strip()
            if len(cleaned) < 2:
                continue
            dedupe_key = cleaned.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(cleaned)
            if len(normalized) >= _MAX_TREND_KEYWORDS:
                break
        return normalized

    @staticmethod
    def merge_domain_weights(
        items: list[TrendDomainWeight],
    ) -> dict[TrendDomain, float]:
        merged: dict[TrendDomain, float] = {}
        for item in items:
            merged[item.domain] = merged.get(item.domain, 0.0) + item.weight
        return merged

    @classmethod
    def llm_output_to_distribution(
        cls,
        output: TrendDomainLLMOutput | None,
    ) -> tuple[DomainDistributionSchema, float]:
        if output is None:
            return DomainDistributionSchema.empty(), 0.0
        merged = cls.merge_domain_weights(output.domains)
        return DomainDistributionSchema.from_scores(merged), output.confidence

    @classmethod
    def llm_output_to_mapping_result(
        cls,
        output: TrendDomainLLMOutput | None,
    ) -> tuple[DomainDistributionSchema, float, list[str]]:
        distribution, confidence = cls.llm_output_to_distribution(output)
        keywords = cls.normalize_trend_keywords(
            output.trend_keywords if output is not None else None
        )
        return distribution, confidence, keywords

    @staticmethod
    def is_score_distribution_ambiguous(scores: DomainScoreMap) -> bool:
        if not scores:
            return True
        ordered = sorted(scores.values(), reverse=True)
        if ordered[0] < CONFIDENCE_THRESHOLD:
            return True
        if len(ordered) >= 2 and (ordered[0] - ordered[1]) < AMBIGUITY_TOP_GAP:
            return True
        return False

    @classmethod
    def needs_grounding(
        cls, confidence: float, distribution: DomainDistributionSchema
    ) -> bool:
        if confidence < CONFIDENCE_THRESHOLD:
            return True
        return cls.is_score_distribution_ambiguous(distribution.scores)

    @staticmethod
    def row_field(row: object, name: str) -> Any:
        if isinstance(row, dict):
            return row.get(name)
        return getattr(row, name, None)

    async def invoke_llm_classifier(
        self,
        *,
        system_instruction: str,
        user_content: str,
        model: str = DEFAULT_LLM_MODEL,
        reason: str,
        **context: Any,
    ) -> tuple[DomainDistributionSchema, float, list[str]]:
        self._log.log_llm_invoked(self.layer, reason=reason, **context)
        timer_key = self._log.begin_timer(self.layer, "llm")
        try:
            result = await invoke_structured_safe(
                system_instruction=system_instruction,
                user_content=user_content,
                schema=TrendDomainLLMOutput,
                temperature=0.2,
                model=model,
                max_output_tokens=4096,
                thinking=False,
                fallback_factory=lambda: TrendDomainLLMOutput(
                    confidence=0.0,
                    domains=[
                        TrendDomainWeight(domain=TrendDomain.TECH_BUSINESS, weight=1.0)
                    ],
                    trend_keywords=["미분류", "일반", "기타"],
                ),
            )
            distribution, confidence, keywords = self.llm_output_to_mapping_result(
                result
            )
            latency_ms = self._log.end_timer(timer_key)
            self._log.log_success(
                self.layer,
                "llm",
                latency_ms=latency_ms,
                result_summary=self._log.summarize_scores(distribution.scores),
                confidence=confidence,
                trend_keywords=keywords,
                **context,
            )
            return distribution, confidence, keywords
        except Exception as exc:
            latency_ms = self._log.end_timer(timer_key)
            self._log.log_failure(
                self.layer,
                "llm",
                latency_ms=latency_ms,
                error=exc,
                **context,
            )
            raise
