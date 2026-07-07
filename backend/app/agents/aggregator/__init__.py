"""어그리게이터(4 에이전트) 패키지 — 외부 진입점."""

from app.agents.aggregator.orchestrator import (
    AggregatorOrchestrator,
    map_behavior_row,
    map_scrap_row,
    map_youtube_row,
)
from app.agents.aggregator.schemas import (
    UNMAPPED_KEY,
    DomainDistributionSchema,
    DomainScoreMap,
    TrendDomainLLMOutput,
    TrendDomainWeight,
    TrendMappingResult,
)

TrendDomainMapper = AggregatorOrchestrator

__all__ = [
    "UNMAPPED_KEY",
    "AggregatorOrchestrator",
    "DomainDistributionSchema",
    "DomainScoreMap",
    "TrendDomainLLMOutput",
    "TrendDomainMapper",
    "TrendDomainWeight",
    "TrendMappingResult",
    "map_behavior_row",
    "map_scrap_row",
    "map_youtube_row",
]
