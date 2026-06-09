from __future__ import annotations

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.subagent.scoring import complete_layer_b


def layer_b_derived_node(state: ProfilerState) -> dict:
    layer_b = complete_layer_b(state["layer_b"], state["axes"])
    log = list(state.get("investigation_log", []))
    log.append(f"layer_b: taste_diversity_index={layer_b.taste_diversity_index}")
    return {
        "layer_b": layer_b,
        "current_step": "layer_b_derived",
        "investigation_log": log,
    }
