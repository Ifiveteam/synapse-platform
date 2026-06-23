"""Aggregator 에이전트 도메인 타입 (파이프라인 내부 계약)."""

from app.agents.aggregator.base.integrated import (
    INTEGRATED_SCHEMA_VERSION,
    IntegratedData,
)
from app.agents.aggregator.base.internal_stats import (
    CognitiveProfileMap,
    InternalUserStats,
    KeywordStat,
    ProfileAxisScore,
)

__all__ = [
    "INTEGRATED_SCHEMA_VERSION",
    "CognitiveProfileMap",
    "IntegratedData",
    "InternalUserStats",
    "KeywordStat",
    "ProfileAxisScore",
]
