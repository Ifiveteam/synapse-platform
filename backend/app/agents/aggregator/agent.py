"""Aggregator 에이전트 진입점."""

from __future__ import annotations

from typing import Optional

from app.agents.aggregator.graph import get_aggregator_graph, get_data_assembly_graph
from app.agents.aggregator.state import AggregatorState
from app.agents.aggregator.trace import (
    log_assemble_workflow_end,
    log_assemble_workflow_start,
    log_workflow_end,
    log_workflow_start,
)

__all__ = [
    "AggregatorAgent",
    "get_aggregator_agent",
]


class AggregatorAgent:
    """Aggregator 멀티 에이전트 메인 클래스."""

    def __init__(self) -> None:
        self._graph = get_aggregator_graph()
        self._assembly_graph = get_data_assembly_graph()

    async def run(
        self,
        *,
        notify_email: str | None = None,
        post_id: str | None = None,
    ) -> AggregatorState:
        """데이터 조립 → 병렬 서브 분석 → 융합 → 검수(Critique) 루프 전체를 실행한다."""
        log_workflow_start()
        initial: AggregatorState = {}
        if notify_email:
            initial["notify_email"] = notify_email
        if post_id:
            initial["post_id"] = post_id
        result: AggregatorState = await self._graph.ainvoke(initial)
        log_workflow_end(result)
        return result

    async def run_assemble_only(self) -> AggregatorState:
        """데이터 조립 서브그래프만 실행한다. Gemini 호출 없이 8각 차트 등 경량 API용."""
        log_assemble_workflow_start()
        result: AggregatorState = await self._assembly_graph.ainvoke({})
        log_assemble_workflow_end(result)
        return result


_aggregator_agent: Optional[AggregatorAgent] = None


def get_aggregator_agent() -> AggregatorAgent:
    global _aggregator_agent
    if _aggregator_agent is None:
        _aggregator_agent = AggregatorAgent()
    return _aggregator_agent
