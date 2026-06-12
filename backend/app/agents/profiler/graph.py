from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.nodes import (
    interpretation_node,
    layer_b_node,
    load_records_node,
    notify_node,
    profile_llm_node,
)


def build_profiler_graph():
    graph = StateGraph(ProfilerState)
    graph.add_node("load_records", load_records_node)
    graph.add_node("layer_b", layer_b_node)
    graph.add_node("profile_llm", profile_llm_node)
    graph.add_node("interpretation", interpretation_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "load_records")
    graph.add_edge("load_records", "layer_b")
    graph.add_edge("layer_b", "profile_llm")
    graph.add_edge("profile_llm", "interpretation")
    graph.add_edge("interpretation", "notify")
    graph.add_edge("notify", END)

    return graph.compile()


profiler_graph = build_profiler_graph()


def run_profiler(user_id: str, email: str) -> dict:
    from app.core.env import load_backend_env

    load_backend_env()
    initial: ProfilerState = {
        "user_id": user_id,
        "notify_email": email,
        "current_step": "pending",
        "records": [],
        "investigation_log": [],
    }
    final = profiler_graph.invoke(initial)
    return final
