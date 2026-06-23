"""Navigator LangGraph 빌드 — 대화형 이상향 설계 (interpret → respond)."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.nodes import interpret, respond
from app.agents.navigator.state import NavigatorState


def build_navigator_graph():
    """START → interpret → respond → END."""
    graph = StateGraph(NavigatorState)
    graph.add_node("interpret", interpret)
    graph.add_node("respond", respond)
    graph.add_edge(START, "interpret")
    graph.add_edge("interpret", "respond")
    graph.add_edge("respond", END)
    return graph.compile()
