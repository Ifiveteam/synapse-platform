"""Aggregator 파이프라인 내부 사용자 통계 도메인 타입."""

from __future__ import annotations

from typing import TypedDict


class KeywordStat(TypedDict):
    keyword: str
    frequency: int
    trend_delta_pct: float


class ProfileAxisScore(TypedDict):
    key: str
    label: str
    avg_score: float


class CognitiveProfileMap(TypedDict):
    axes: list[ProfileAxisScore]
    cohort_size: int
    measurement_period: str


class InternalUserStats(TypedDict):
    top_keywords: list[KeywordStat]
    cognitive_bias_map: CognitiveProfileMap
