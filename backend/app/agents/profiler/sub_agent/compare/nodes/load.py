"""스냅샷 2개 로드."""

from __future__ import annotations

import uuid

from app.agents.profiler.sub_agent.compare.state import CompareState


async def node_load(state: CompareState) -> dict:
    log = list(state.get("run_log") or [])
    user_id = uuid.UUID(str(state["user_id"]))
    from_id = uuid.UUID(str(state["from_snapshot_id"]))
    to_id = uuid.UUID(str(state["to_snapshot_id"]))

    from app.core.database.session import AsyncSessionLocal
    from app.repositories.profiler_repository import fetch_profile_snapshot

    async with AsyncSessionLocal() as session:
        from_row = await fetch_profile_snapshot(session, user_id, from_id)
        to_row = await fetch_profile_snapshot(session, user_id, to_id)

    if from_row is None or to_row is None:
        log.append("load: snapshot not found")
        return {"error": "snapshot_not_found", "run_log": log}

    log.append(f"load: from={from_id} to={to_id}")
    return {
        "from_row": from_row,
        "to_row": to_row,
        "error": None,
        "run_log": log,
    }
