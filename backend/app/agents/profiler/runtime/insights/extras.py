"""Mock-backed API extras: ideal-gap and behavior events."""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    AxesDelta,
    BehaviorEvent,
    BehaviorEventSummary,
    IdealGap,
    IdealProfile,
    LayerBDelta,
    ProfilerResult,
)

_PROFILER_ROOT = Path(__file__).resolve().parent.parent.parent
_IDEAL_DIR = _PROFILER_ROOT / "mocks" / "ideal"
_EVENTS_DIR = _PROFILER_ROOT / "mocks" / "events"


def load_ideal_profile(user_id: str) -> IdealProfile | None:
    path = _IDEAL_DIR / f"{user_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return IdealProfile.model_validate(data)


def compute_ideal_gap(user_id: str, current: ProfilerResult) -> IdealGap | None:
    ideal = load_ideal_profile(user_id)
    if ideal is None:
        return None

    axes_gap = {
        key: float(getattr(ideal.axes, key)) - float(getattr(current.axes, key))
        for key in SYNAPSE_AXIS_KEYS
    }
    layer_b_gap = LayerBDelta(
        search_active_ratio=round(
            ideal.layer_b.search_active_ratio - current.layer_b.search_active_ratio,
            3,
        ),
        viewing_concentration=round(
            ideal.layer_b.viewing_concentration - current.layer_b.viewing_concentration,
            3,
        ),
        taste_diversity_index=round(
            ideal.layer_b.taste_diversity_index - current.layer_b.taste_diversity_index,
            1,
        ),
        exploration_depth=round(
            ideal.layer_b.exploration_depth - current.layer_b.exploration_depth,
            3,
        ),
    )

    achievement: dict[str, float] = {}
    for key in SYNAPSE_AXIS_KEYS:
        target = float(getattr(ideal.axes, key))
        value = float(getattr(current.axes, key))
        if target <= 0:
            achievement[key] = 100.0
        else:
            achievement[key] = round(min(100.0, value / target * 100), 1)

    return IdealGap(
        user_id=user_id,
        axes_gap=AxesDelta(**axes_gap),
        layer_b_gap=layer_b_gap,
        axis_achievement_pct=achievement,
    )


def load_behavior_events(user_id: str) -> list[BehaviorEvent]:
    path = _EVENTS_DIR / f"{user_id}.jsonl"
    if not path.exists():
        return []
    events: list[BehaviorEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(BehaviorEvent.model_validate(json.loads(line)))
    return events


def summarize_behavior_events(user_id: str) -> BehaviorEventSummary:
    events = load_behavior_events(user_id)
    dwell = sum(event.duration_ms or 0 for event in events)
    clicks = sum(1 for event in events if event.event_type == "click")
    return BehaviorEventSummary(
        total_events=len(events),
        total_dwell_ms=dwell,
        click_count=clicks,
    )
