"""Aggregator LangGraph 워크플로우."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.aggregator.nodes import (
    assemble_data_node,
    culture_analysis_node,
    generate_report_node,
    market_analysis_node,
    notify_node,
    verify_report_node,
)
from app.agents.aggregator.routing import route_after_verify
from app.agents.aggregator.state import AggregatorState

_aggregator_graph = None
_data_assembly_graph = None


def build_aggregator_graph():
    graph = StateGraph(AggregatorState)

    graph.add_node("assemble_data", assemble_data_node)
    graph.add_node("culture_analysis", culture_analysis_node)
    graph.add_node("market_analysis", market_analysis_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("verify_report", verify_report_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "assemble_data")

    # Map: assemble_data 이후 culture·market 병렬 실행
    graph.add_edge("assemble_data", "culture_analysis")
    graph.add_edge("assemble_data", "market_analysis")

    # Reduce: 두 서브 에이전트 완료 후 마스터 융합
    graph.add_edge("culture_analysis", "generate_report")
    graph.add_edge("market_analysis", "generate_report")

    graph.add_edge("generate_report", "verify_report")

    # Critique 루프: 마스터 재융합 / culture·market 역주행 / 양쪽 병렬 재분석
    graph.add_conditional_edges(
        "verify_report",
        route_after_verify,
        {
            "__end__": "notify",
            "generate_report": "generate_report",
            "culture_analysis": "culture_analysis",
            "market_analysis": "market_analysis",
        },
    )

    graph.add_edge("notify", END)

    return graph.compile()


def build_data_assembly_graph():
    """데이터 조립만 수행하는 경량 서브그래프 (Gemini 미호출)."""
    graph = StateGraph(AggregatorState)
    graph.add_node("assemble_data", assemble_data_node)
    graph.add_edge(START, "assemble_data")
    graph.add_edge("assemble_data", END)
    return graph.compile()


def get_aggregator_graph():
    global _aggregator_graph
    if _aggregator_graph is None:
        _aggregator_graph = build_aggregator_graph()
    return _aggregator_graph


def get_data_assembly_graph():
    global _data_assembly_graph
    if _data_assembly_graph is None:
        _data_assembly_graph = build_data_assembly_graph()
    return _data_assembly_graph
