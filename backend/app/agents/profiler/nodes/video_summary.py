"""video_summary 서브 에이전트 노드 — 메인 profiler graph에서 invoke."""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.sub_agent import run_video_summary


async def video_summary_node(state: ProfilerState) -> dict[str, Any]:
    """catalog 미분석 행을 영상요약 서브그래프로 처리 → video_analysis."""
    user_id = uuid.UUID(str(state["user_id"]))
    limit = state.get("analysis_limit")

    result = await run_video_summary(user_id, limit)

    log_lines = list(state.get("investigation_log") or [])
    log_lines.append(
        "video_summary: "
        f"saved={result.get('saved_count') or 0} "
        f"skipped={result.get('skipped_count') or 0}"
    )
    if result.get("error"):
        log_lines.append(f"video_summary error: {result['error']}")
    if result.get("run_log"):
        log_lines.append(result["run_log"])

    return {
        "current_step": "video_summary",
        "video_summary_saved_count": result.get("saved_count"),
        "video_summary_skipped_count": result.get("skipped_count"),
        "video_summary_error": result.get("error"),
        "investigation_log": log_lines,
    }
