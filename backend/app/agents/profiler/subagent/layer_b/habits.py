from __future__ import annotations

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.subagent.patterns import compute_behavior_patterns
from app.agents.profiler.subagent.scoring import (
    compute_layer_b_habits,
    get_channel_breakdown,
)


def layer_b_habits_node(state: ProfilerState) -> dict:
    records = state["records"]
    layer_b = compute_layer_b_habits(records)
    channels = get_channel_breakdown(records)
    top_channel = next(iter(channels), ("none", 0))
    log = state.get("investigation_log", [])
    log = [
        *log,
        f"layer_b: search_active_ratio={layer_b.search_active_ratio}",
        f"layer_b: viewing_concentration={layer_b.viewing_concentration}",
        f"layer_b: exploration_depth={layer_b.exploration_depth}",
        f"top channel by watch time: {top_channel[0]} ({top_channel[1]}s)",
    ]
    patterns = compute_behavior_patterns(records)
    log.append(f"patterns: weekend_ratio={patterns.weekend_ratio}")
    return {
        "layer_b": layer_b,
        "behavior_patterns": patterns,
        "current_step": "layer_b_habits",
        "investigation_log": log,
    }
