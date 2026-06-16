from __future__ import annotations

import time
import uuid

from langgraph.graph import END, StateGraph

from app.agents.profiler.video_summary.nodes import (
    node_build_embedding_text,
    node_embed,
    node_fetch_unanalyzed,
    node_log,
    node_store_analysis,
    node_summarize,
)
from app.agents.profiler.video_summary.state import VideoSummaryState


def should_continue(state: VideoSummaryState) -> str:
    """에러면 바로 log로 모아 보고 후 종료."""
    return "log" if state.get("error") else "continue"


def route_after_fetch(state: VideoSummaryState) -> str:
    if state.get("error") or not state.get("watches"):
        return "log"
    return "summarize"


builder = StateGraph(VideoSummaryState)

builder.add_node("fetch", node_fetch_unanalyzed)
builder.add_node("summarize", node_summarize)
builder.add_node("build_text", node_build_embedding_text)
builder.add_node("embed", node_embed)
builder.add_node("store", node_store_analysis)
builder.add_node("log", node_log)

builder.set_entry_point("fetch")

builder.add_conditional_edges(
    "fetch", route_after_fetch, {"summarize": "summarize", "log": "log"}
)
builder.add_conditional_edges(
    "summarize", should_continue, {"continue": "build_text", "log": "log"}
)
builder.add_edge("build_text", "embed")
builder.add_conditional_edges(
    "embed", should_continue, {"continue": "store", "log": "log"}
)
builder.add_edge("store", "log")
builder.add_edge("log", END)

video_summary_graph = builder.compile()


async def run_video_summary(
    user_id: uuid.UUID, limit: int | None = None
) -> VideoSummaryState:
    """영상요약 서브에이전트 실행 엔트리포인트."""
    initial: VideoSummaryState = {
        "user_id": user_id,
        "limit": limit,
        "watches": [],
        "analyzed": [],
        "saved_count": None,
        "skipped_count": None,
        "error": None,
        "started_at": time.time(),
        "run_log": None,
    }
    return await video_summary_graph.ainvoke(initial)
