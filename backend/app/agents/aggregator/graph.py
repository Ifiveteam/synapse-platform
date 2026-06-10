"""Aggregator LangGraph 워크플로우."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.aggregator.nodes import assemble_data_node, generate_report_node
from app.agents.aggregator.state import AggregatorState

_aggregator_graph = None


def build_aggregator_graph():
    graph = StateGraph(AggregatorState)
    graph.add_node("assemble_data", assemble_data_node)
    graph.add_node("generate_report", generate_report_node)

    graph.add_edge(START, "assemble_data")
    graph.add_edge("assemble_data", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


def get_aggregator_graph():
    global _aggregator_graph
    if _aggregator_graph is None:
        _aggregator_graph = build_aggregator_graph()
    return _aggregator_graph
