from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.profiler.nodes import (
    build_profile_node,
    notify_node,
    video_summary_node,
)
from app.agents.profiler.state import ProfilerState


def build_profiler_graph():
    graph = StateGraph(ProfilerState)
    graph.add_node("video_summary", video_summary_node)
    graph.add_node("build_profile", build_profile_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "video_summary")
    graph.add_edge("video_summary", "build_profile")
    graph.add_edge("build_profile", "notify")
    graph.add_edge("notify", END)

    return graph.compile()


profiler_graph = build_profiler_graph()


def run_profiler(
    user_id: str, email: str, *, analysis_limit: int | None = None
) -> dict:
    import asyncio

    return asyncio.run(
        run_profiler_async(user_id, email, analysis_limit=analysis_limit)
    )


async def run_profiler_async(
    user_id: str, email: str, *, analysis_limit: int | None = None
) -> dict:
    from app.core.env import load_backend_env

    load_backend_env()
    initial: ProfilerState = {
        "user_id": user_id,
        "notify_email": email,
        "current_step": "pending",
        "investigation_log": [],
        "analysis_limit": analysis_limit,
    }
    return await profiler_graph.ainvoke(initial)
