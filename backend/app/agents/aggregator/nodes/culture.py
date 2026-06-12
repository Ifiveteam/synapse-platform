"""culture_analysis 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.nodes._helpers import NODE_CULTURE, require_integrated_data
from app.agents.aggregator.routing import critique_for_culture
from app.agents.aggregator.state import AggregatorState
from app.agents.aggregator.sub_agent import run_culture_analysis
from app.agents.aggregator.trace import (
    log_analysis_result,
    log_culture_input,
    log_node_enter,
    logger,
)


async def culture_analysis_node(state: AggregatorState) -> dict[str, Any]:
    """서브 에이전트 1: 문화/콘텐츠 관점 트렌드 격차 분석 초안."""
    log_node_enter(NODE_CULTURE, state=state)
    integrated_data = require_integrated_data(state)
    critique_feedback = critique_for_culture(state)
    log_culture_input(integrated_data)
    if critique_feedback:
        logger.info(
            "  └─ 검수 피드백 반영 culture 재분석 (revision_target=%s)",
            state.get("revision_target"),
        )
    culture_analysis = await run_culture_analysis(
        integrated_data,
        critique_feedback=critique_feedback,
    )
    log_analysis_result(agent="culture_analysis", content=culture_analysis)
    return {"culture_analysis": culture_analysis}
