"""Aggregator LangGraph 워크플로우 상태."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from app.agents.aggregator.base import IntegratedData


class AggregatorState(TypedDict):
    """LangGraph 실행 상태."""

    integrated_data: NotRequired[IntegratedData]
    report_markdown: NotRequired[str]
    error: NotRequired[str]
