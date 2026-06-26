from __future__ import annotations

import time

from app.agents.profiler.sub_agent.video_summary.state import VideoSummaryState


def _run_log(state: VideoSummaryState) -> str:
    elapsed = time.time() - (state.get("started_at") or time.time())
    fetched = len(state.get("catalogs") or [])
    analyzed = len(state.get("analyzed") or [])
    skipped = state.get("skipped_count") or 0
    saved = state.get("saved_count") or 0
    lines = [
        "=" * 50,
        "[Profiler/VideoSummary] ?? ??",
        f"  ??(??):  {fetched:,}?",
        f"  ?? ??:   {analyzed:,}?",
        f"  ??:        {skipped:,}?",
        f"  DB ??:     {saved:,}?",
        f"  ????:    {elapsed:.1f}s",
    ]
    if state.get("error"):
        lines.append(f"  [??] {state['error']}")
    lines.append("=" * 50)
    return "\n".join(lines)


async def node_store_analysis(state: VideoSummaryState) -> VideoSummaryState:
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import upsert_video_analysis

        analyzed = state.get("analyzed") or []
        async with AsyncSessionLocal() as session:
            saved = await upsert_video_analysis(session, analyzed)
            await session.commit()
        result = {**state, "saved_count": saved, "error": None}
    except Exception as e:
        result = {**state, "saved_count": 0, "error": str(e)}

    run_log = _run_log(result)
    print(run_log)
    return {**result, "run_log": run_log}
