"""Aggregator LangGraph 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.pipeline import assemble_integrated_data
from app.agents.aggregator.report import generate_b2b_report
from app.agents.aggregator.state import AggregatorState


async def assemble_data_node(_state: AggregatorState) -> dict[str, Any]:
    """LangGraph 노드: 내부·외부 데이터를 조립해 integrated_data를 상태에 기록한다."""
    integrated_data = await assemble_integrated_data()
    return {"integrated_data": integrated_data, "error": None}


async def generate_report_node(state: AggregatorState) -> dict[str, Any]:
    """LangGraph 노드: 통합 데이터를 입력받아 Markdown 리포트를 상태에 기록한다."""
    integrated_data = state.get("integrated_data")
    if integrated_data is None:
        msg = (
            "integrated_data가 상태에 없습니다. "
            "assemble_data 노드 이후에 실행하세요."
        )
        raise ValueError(msg)

    report_markdown = await generate_b2b_report(integrated_data)

    return {
        "integrated_data": integrated_data,
        "report_markdown": report_markdown,
        "error": None,
    }
