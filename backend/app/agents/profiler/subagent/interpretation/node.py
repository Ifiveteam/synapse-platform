from __future__ import annotations

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.subagent.interpretation.rules import compute_interpretation


def interpretation_node(state: ProfilerState) -> dict:
    interpretation = compute_interpretation(state["axes"], state["layer_b"])
    log = list(state.get("investigation_log", []))
    log.append(f"interpretation: mode={interpretation.consumption_mode}")
    log.append(f"interpretation: lever={interpretation.primary_lever}")
    log.append(f"interpretation: verdict={interpretation.sovereignty_verdict}")
    return {
        "interpretation": interpretation,
        "current_step": "interpretation",
        "investigation_log": log,
    }
