"""generate_report 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.nodes._helpers import NODE_GENERATE, require_integrated_data
from app.agents.aggregator.report import generate_fused_b2b_report
from app.agents.aggregator.routing import critique_for_master_report
from app.agents.aggregator.state import AggregatorState
from app.agents.aggregator.trace import (
    log_node_enter,
    log_report_generation,
    log_report_result,
)


async def generate_report_node(state: AggregatorState) -> dict[str, Any]:
    """마스터 에이전트: 서브 에이전트 초안을 융합해 최종 JSON 리포트를 생성한다."""
    log_node_enter(NODE_GENERATE, state=state)
    integrated_data = require_integrated_data(state)

    culture_analysis = state.get("culture_analysis")
    market_analysis = state.get("market_analysis")
    if not culture_analysis or not market_analysis:
        msg = (
            "culture_analysis·market_analysis가 모두 필요합니다. "
            "병렬 분석 노드 완료 후 실행하세요."
        )
        raise ValueError(msg)

    critique_feedback = critique_for_master_report(state)
    log_report_generation(
        culture_chars=len(culture_analysis),
        market_chars=len(market_analysis),
        has_critique=bool(critique_feedback),
        critique_preview=critique_feedback,
    )

    report_json = await generate_fused_b2b_report(
        integrated_data,
        culture_analysis=culture_analysis,
        market_analysis=market_analysis,
        critique_feedback=critique_feedback,
    )
    log_report_result(report_json)

    return {
        "report_json": report_json.model_dump(),
        "error": None,
    }
