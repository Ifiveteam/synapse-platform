from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.agents.profiler.base import (
    TASTE_DIVERSITY_AXES,
    BehaviorPatterns,
    IndexedRecord,
    LayerB,
    Synapse8Axes,
)
from app.agents.profiler.state import ProfilerState
from app.agents.profiler.tools import (
    filter_search_records,
    filter_watch_records,
    get_channel_breakdown,
    trail_from_search,
)

_EXPLORATION_CHAIN_GAP_HOURS = 24
_EXPLORATION_DURATION_NORM_SEC = 1200
_EXPLORATION_COUNT_NORM = 5
_HOUR_BUCKETS = ("morning", "afternoon", "evening", "night")


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _norm_ratio(value: float, norm: float) -> float:
    if norm <= 0:
        return 0.0
    return _clamp_unit(value / norm)


def _compute_search_active_ratio(records: list[IndexedRecord]) -> float:
    total = len(records) or 1
    return round(len(filter_search_records(records)) / total, 3)


def _compute_viewing_concentration(records: list[IndexedRecord]) -> float:
    channel_breakdown = get_channel_breakdown(records)
    if not channel_breakdown:
        return 0.0
    total_watch_sec = sum(channel_breakdown.values()) or 1
    top_channel_sec = max(channel_breakdown.values())
    concentration = top_channel_sec / total_watch_sec
    unique_channels = len(channel_breakdown)
    channel_factor = 1.0 / max(unique_channels, 1)
    return round(_clamp_unit(concentration * 0.7 + channel_factor * 0.3), 3)


def _thread_score(trail: list[IndexedRecord]) -> float:
    if not trail:
        return 0.0
    total_duration = sum(record.duration_sec or 0 for record in trail)
    count = len(trail)
    return 0.6 * _norm_ratio(
        total_duration, _EXPLORATION_DURATION_NORM_SEC
    ) + 0.4 * _norm_ratio(count, _EXPLORATION_COUNT_NORM)


def _compute_exploration_depth(records: list[IndexedRecord]) -> float:
    searches = [r for r in filter_search_records(records) if r.recorded_at]
    if not searches:
        return 0.0
    watches = filter_watch_records(records)
    scores = [
        _thread_score(
            trail_from_search(
                search, watches, gap_hours=_EXPLORATION_CHAIN_GAP_HOURS
            )
        )
        for search in searches
    ]
    return round(sum(scores) / len(scores), 3)


def _compute_layer_b_habits(records: list[IndexedRecord]) -> LayerB:
    return LayerB(
        search_active_ratio=_compute_search_active_ratio(records),
        viewing_concentration=_compute_viewing_concentration(records),
        taste_diversity_index=0.0,
        exploration_depth=_compute_exploration_depth(records),
    )


def _hour_bucket(dt: datetime) -> str:
    hour = dt.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _compute_behavior_patterns(records: list[IndexedRecord]) -> BehaviorPatterns:
    bucket_counts: Counter[str] = Counter()
    weekend_count = 0
    dated_count = 0
    channel_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()

    for record in records:
        for tag in record.tags:
            tag_counts[tag] += 1
        if record.source_type == "watch" and record.channel:
            channel_counts[record.channel] += 1
        if record.recorded_at is None:
            continue
        dt = record.recorded_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dated_count += 1
        bucket_counts[_hour_bucket(dt)] += 1
        if dt.weekday() >= 5:
            weekend_count += 1

    total_buckets = sum(bucket_counts.values()) or 1
    hour_distribution = {
        bucket: round(bucket_counts.get(bucket, 0) / total_buckets, 3)
        for bucket in _HOUR_BUCKETS
    }
    weekend_ratio = round(weekend_count / dated_count, 3) if dated_count else 0.0

    watches = filter_watch_records(records)
    channel_repeat: Counter[str] = Counter()
    for record in watches:
        if record.channel:
            channel_repeat[record.channel] += 1

    return BehaviorPatterns(
        hour_distribution=hour_distribution,
        weekend_ratio=weekend_ratio,
        top_repeated_channels=[
            {"channel": name, "count": count}
            for name, count in channel_repeat.most_common(5)
        ],
        top_repeated_tags=[
            {"tag": name, "count": count}
            for name, count in tag_counts.most_common(8)
        ],
    )


def _clamp_score(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _compute_taste_diversity_index(axes: Synapse8Axes) -> float:
    values = [float(getattr(axes, key)) for key in TASTE_DIVERSITY_AXES]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = variance**0.5
    return round(_clamp_score(100 - std * 2.5), 1)


def complete_layer_b(partial: LayerB, axes: Synapse8Axes) -> LayerB:
    return LayerB(
        search_active_ratio=partial.search_active_ratio,
        viewing_concentration=partial.viewing_concentration,
        taste_diversity_index=_compute_taste_diversity_index(axes),
        exploration_depth=partial.exploration_depth,
    )


def layer_b_node(state: ProfilerState) -> dict:
    records = state["records"]
    layer_b = _compute_layer_b_habits(records)
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
    patterns = _compute_behavior_patterns(records)
    log.append(f"patterns: weekend_ratio={patterns.weekend_ratio}")
    return {
        "layer_b": layer_b,
        "behavior_patterns": patterns,
        "current_step": "layer_b",
        "investigation_log": log,
    }
