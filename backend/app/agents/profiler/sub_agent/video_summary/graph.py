from __future__ import annotations

import time
import uuid

from langgraph.graph import END, StateGraph

from app.agents.profiler.sub_agent.video_summary.nodes import (
    node_embed,
    node_select,
    node_store_analysis,
    node_summarize,
)
from app.agents.profiler.sub_agent.video_summary.state import VideoSummaryState


def route_after_select(state: VideoSummaryState) -> str:
    if state.get("error") or not state.get("catalogs"):
        return "store"
    return "summarize"


def route_on_error(state: VideoSummaryState) -> str:
    return "store" if state.get("error") else "embed"


builder = StateGraph(VideoSummaryState)

builder.add_node("select", node_select)
builder.add_node("summarize", node_summarize)
builder.add_node("embed", node_embed)
builder.add_node("store", node_store_analysis)

builder.set_entry_point("select")

builder.add_conditional_edges(
    "select", route_after_select, {"summarize": "summarize", "store": "store"}
)
builder.add_conditional_edges(
    "summarize", route_on_error, {"embed": "embed", "store": "store"}
)
builder.add_edge("embed", "store")
builder.add_edge("store", END)

video_summary_graph = builder.compile()


async def run_video_summary(
    user_id: uuid.UUID,
    limit: int | None = None,
    analysis_source_ids: list[str] | None = None,
) -> VideoSummaryState:
    initial: VideoSummaryState = {
        "user_id": user_id,
        "limit": limit,
        "analysis_source_ids": analysis_source_ids,
        "catalogs": [],
        "analyzed": [],
        "saved_count": None,
        "skipped_count": None,
        "error": None,
        "started_at": time.time(),
        "run_log": None,
    }
    return await video_summary_graph.ainvoke(initial)
