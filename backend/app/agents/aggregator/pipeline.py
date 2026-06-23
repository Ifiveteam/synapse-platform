"""Aggregator 파이프라인 데이터 조립."""

from __future__ import annotations

from datetime import UTC, datetime

from app.agents.aggregator.base import INTEGRATED_SCHEMA_VERSION, IntegratedData
from app.agents.aggregator.mock_data import generate_internal_user_stats
from app.services import external_trends


async def assemble_integrated_data() -> IntegratedData:
    """내부 Mock 통계와 외부 실시간 트렌드를 조립한 통합 데이터를 반환한다."""
    user_mock = generate_internal_user_stats()
    external_real = await external_trends.fetch_real_trends()

    return {
        "schema_version": INTEGRATED_SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "internal_user_stats": user_mock,
        "external_market_trends": external_real,
    }
