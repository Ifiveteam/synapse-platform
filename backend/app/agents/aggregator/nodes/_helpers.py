"""Aggregator LangGraph 노드 공유 헬퍼."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.state import AggregatorState

NODE_ASSEMBLE = "assemble_data"
NODE_CULTURE = "culture_analysis"
NODE_MARKET = "market_analysis"
NODE_GENERATE = "generate_report"
NODE_VERIFY = "verify_report"
NODE_NOTIFY = "notify"


def require_integrated_data(state: AggregatorState) -> dict[str, Any]:
    integrated_data = state.get("integrated_data")
    if integrated_data is None:
        msg = "integrated_data가 상태에 없습니다. assemble_data 노드 이후에 실행하세요."
        raise ValueError(msg)
    return integrated_data
