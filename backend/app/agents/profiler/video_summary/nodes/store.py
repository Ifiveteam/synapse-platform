from __future__ import annotations

import time

from app.agents.profiler.video_summary.state import VideoSummaryState


async def node_store_analysis(state: VideoSummaryState) -> VideoSummaryState:
    """분석 결과를 video_analysis에 upsert."""
    try:
        from app.agents.profiler.video_summary.repository import upsert_video_analysis
        from app.core.database.session import AsyncSessionLocal

        analyzed = state.get("analyzed") or []
        async with AsyncSessionLocal() as session:
            saved = await upsert_video_analysis(session, analyzed)
        return {**state, "saved_count": saved, "error": None}
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}


def node_log(state: VideoSummaryState) -> VideoSummaryState:
    elapsed = time.time() - (state.get("started_at") or time.time())
    fetched = len(state.get("watches") or [])
    analyzed = len(state.get("analyzed") or [])
    skipped = state.get("skipped_count") or 0
    saved = state.get("saved_count") or 0

    lines = [
        "=" * 50,
        "[Profiler/VideoSummary] 파이프라인 완료",
        f"  조회(미분석):  {fetched:,}건",
        f"  분석 성공:     {analyzed:,}건",
        f"  스킵:          {skipped:,}건",
        f"  DB 저장:       {saved:,}건",
        f"  소요시간:      {elapsed:.1f}s",
    ]
    if state.get("error"):
        lines.append(f"  [이상] 에러 발생: {state['error']}")
    lines.append("=" * 50)

    run_log = "\n".join(lines)
    print(run_log)
    return {**state, "run_log": run_log}
