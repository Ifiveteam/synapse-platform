"""assemble_data 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.nodes._helpers import NODE_ASSEMBLE
from app.agents.aggregator.pipeline import assemble_integrated_data
from app.agents.aggregator.state import AggregatorState
from app.agents.aggregator.trace import log_integrated_data_summary, log_node_enter


async def assemble_data_node(_state: AggregatorState) -> dict[str, Any]:
    """내부·외부 데이터를 조립해 integrated_data를 상태에 기록한다."""
    log_node_enter(NODE_ASSEMBLE)
    integrated_data = await assemble_integrated_data()
    log_integrated_data_summary(integrated_data)
    return {
        "integrated_data": integrated_data,
        "review_count": 0,
        "revision_target": "generate_report",
        "error": None,
    }
