"""Aggregator 에이전트 진입점."""

from __future__ import annotations

from typing import Optional

from app.agents.aggregator.base import IntegratedData
from app.agents.aggregator.graph import get_aggregator_graph
from app.agents.aggregator.pipeline import assemble_integrated_data
from app.agents.aggregator.report import generate_b2b_report
from app.agents.aggregator.state import AggregatorState

__all__ = [
    "AggregatorAgent",
    "assemble_integrated_data",
    "get_aggregator_agent",
]


class AggregatorAgent:
    """Aggregator 에이전트 메인 클래스."""

    def __init__(self) -> None:
        self._graph = get_aggregator_graph()

    async def assemble_integrated_data(self) -> IntegratedData:
        return await assemble_integrated_data()

    async def generate_report(
        self,
        data: IntegratedData,
        *,
        model: str | None = None,
    ) -> str:
        return await generate_b2b_report(data, model=model)

    async def run(self) -> AggregatorState:
        """통합 데이터 조립 → 리포트 생성 전체 파이프라인을 실행한다."""
        result = await self._graph.ainvoke({})
        return result


_aggregator_agent: Optional[AggregatorAgent] = None


def get_aggregator_agent() -> AggregatorAgent:
    global _aggregator_agent
    if _aggregator_agent is None:
        _aggregator_agent = AggregatorAgent()
    return _aggregator_agent
