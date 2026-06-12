"""market_analysis 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.nodes._helpers import NODE_MARKET, require_integrated_data
from app.agents.aggregator.routing import critique_for_market
from app.agents.aggregator.state import AggregatorState
from app.agents.aggregator.sub_agent import run_market_analysis
from app.agents.aggregator.trace import (
    log_analysis_result,
    log_market_input,
    log_node_enter,
    logger,
)


async def market_analysis_node(state: AggregatorState) -> dict[str, Any]:
    """서브 에이전트 2: 매크로 시장·언론 경제 이슈 분석 초안."""
    log_node_enter(NODE_MARKET, state=state)
    integrated_data = require_integrated_data(state)
    critique_feedback = critique_for_market(state)
    log_market_input(integrated_data)
    if critique_feedback:
        logger.info(
            "  └─ 검수 피드백 반영 market 재분석 (revision_target=%s)",
            state.get("revision_target"),
        )
    market_analysis = await run_market_analysis(
        integrated_data,
        critique_feedback=critique_feedback,
    )
    log_analysis_result(agent="market_analysis", content=market_analysis)
    return {"market_analysis": market_analysis}
