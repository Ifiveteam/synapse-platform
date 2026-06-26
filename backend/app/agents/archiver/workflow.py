"""Archiver LangGraph StateGraph — 병렬 수집 fan-out / fan-in 오케스트레이션."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.archiver.branches import route_after_evaluator, route_after_router
from app.agents.archiver.nodes import collect_node, rag_node, search_node
from app.agents.archiver.models import (
    COLLECT_NODE,
    RAG_NODE,
    SEARCH_NODE,
    ArchiverState,
)
from app.agents.archiver.steps import classify, evaluate, need_dom, respond

_ENGINE_NODES = (COLLECT_NODE, RAG_NODE, SEARCH_NODE)
# router 분기: respond=GENERAL 프리패스 | need_dom | 1차 병렬 fan-out
_ROUTER_DESTINATIONS = (*_ENGINE_NODES, "need_dom", "respond")
_EVALUATOR_DESTINATIONS = (*_ENGINE_NODES, "respond")


def build_archiver_workflow():
    """router 후 (GENERAL→respond | fan-out→evaluator 루프) → respond."""
    graph = StateGraph(ArchiverState)

    graph.add_node("router", classify)
    graph.add_node(COLLECT_NODE, collect_node)
    graph.add_node(RAG_NODE, rag_node)
    graph.add_node(SEARCH_NODE, search_node)
    graph.add_node("evaluator", evaluate)
    graph.add_node("need_dom", need_dom)
    graph.add_node("respond", respond)

    graph.add_edge(START, "router")

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {dest: dest for dest in _ROUTER_DESTINATIONS},
    )

    # 수집 엔진 → evaluator fan-in · GENERAL 프리패스는 router에서 respond로 직행
    for engine in _ENGINE_NODES:
        graph.add_edge(engine, "evaluator")

    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {dest: dest for dest in _EVALUATOR_DESTINATIONS},
    )

    graph.add_edge("need_dom", END)
    graph.add_edge("respond", END)

    return graph.compile()
