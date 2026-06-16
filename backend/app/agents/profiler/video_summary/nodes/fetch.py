from __future__ import annotations

from app.agents.profiler.video_summary.state import VideoSummaryState, WatchInput


async def node_fetch_unanalyzed(state: VideoSummaryState) -> VideoSummaryState:
    """아직 분석되지 않은 user_video_watch를 읽어 WatchInput 리스트로."""
    try:
        from app.agents.profiler.video_summary.repository import (
            fetch_unanalyzed_watches,
        )
        from app.core.database.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            rows = await fetch_unanalyzed_watches(
                session, state["user_id"], state.get("limit")
            )

        watches: list[WatchInput] = [
            {
                "watch_id": row.id,
                "title": row.title,
                "channel": row.channel,
                "description": row.description,
                "transcript": row.transcript,
                "tags": row.tags,
                "category": row.category,
            }
            for row in rows
        ]
        return {**state, "watches": watches, "error": None}
    except Exception as e:
        return {**state, "watches": [], "error": str(e)}
