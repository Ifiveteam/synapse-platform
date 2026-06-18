from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.profiler.sub_agent.compare.nodes import (
    node_diff,
    node_load,
    node_summarize,
)
from app.agents.profiler.sub_agent.compare.state import CompareState


def _route_after_load(state: CompareState) -> str:
    if state.get("error"):
        return "end"
    return "diff"


def build_compare_graph():
    graph = StateGraph(CompareState)
    graph.add_node("load", node_load)
    graph.add_node("diff", node_diff)
    graph.add_node("summarize", node_summarize)

    graph.add_edge(START, "load")
    graph.add_conditional_edges(
        "load",
        _route_after_load,
        {"diff": "diff", "end": END},
    )
    graph.add_edge("diff", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


compare_graph = build_compare_graph()


async def run_compare(
    user_id: str,
    from_snapshot_id: str,
    to_snapshot_id: str,
) -> CompareState:
    from app.core.env import load_backend_env

    load_backend_env()
    initial: CompareState = {
        "user_id": user_id,
        "from_snapshot_id": from_snapshot_id,
        "to_snapshot_id": to_snapshot_id,
        "run_log": [],
    }
    return await compare_graph.ainvoke(initial)


def compare_state_to_api_payload(result: CompareState) -> dict[str, Any] | None:
    """에이전트 실행 결과 → HTTP 응답 dict."""
    if result.get("error"):
        return None

    diff = result.get("diff")
    if not diff:
        return None

    payload = dict(diff)
    narrative = result.get("narrative")
    if narrative:
        payload["narrative"] = narrative
    payload["narrative_error"] = result.get("narrative_error")
    return payload
