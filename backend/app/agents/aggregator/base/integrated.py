"""Aggregator 파이프라인 통합 데이터 도메인 타입."""

from __future__ import annotations

from typing import TypedDict

from app.agents.aggregator.base.internal_stats import InternalUserStats
from app.services.external_trends import ExternalMarketTrends

INTEGRATED_SCHEMA_VERSION = "0.2.0"


class IntegratedData(TypedDict):
    schema_version: str
    generated_at: str
    internal_user_stats: InternalUserStats
    external_market_trends: ExternalMarketTrends
