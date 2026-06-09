from __future__ import annotations

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.subagent.load_records.loader import load_mock_bundle


def load_records_node(state: ProfilerState) -> dict:
    bundle = load_mock_bundle(state["user_id"])
    return {
        "records": bundle.records,
        "current_step": "load_records",
        "investigation_log": [f"loaded {len(bundle.records)} indexed records"],
    }
