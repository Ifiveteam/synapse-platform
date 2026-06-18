"""결정론적 diff 산출."""

from __future__ import annotations

from app.agents.profiler.sub_agent.compare.state import CompareState
from app.agents.profiler.sub_agent.compare.tool import compare_profile_snapshots


async def node_diff(state: CompareState) -> dict:
    log = list(state.get("run_log") or [])

    if state.get("error"):
        return {}

    from_row = state.get("from_row")
    to_row = state.get("to_row")
    if from_row is None or to_row is None:
        return {"error": "snapshot_not_found", "run_log": log + ["diff: missing rows"]}

    diff = compare_profile_snapshots(from_row, to_row)
    log.append("diff: computed scores/habits/traits delta")
    return {"diff": diff, "run_log": log}
