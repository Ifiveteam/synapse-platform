from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    TASTE_DIVERSITY_AXES,
    IndexedRecord,
    LayerB,
    ProfilerAnalysisOutput,
    Synapse8Axes,
    Top5Interest,
)

EXPLORATION_CHAIN_GAP_HOURS = 24
EXPLORATION_DURATION_NORM_SEC = 1200
EXPLORATION_COUNT_NORM = 5

TAG_AXIS_WEIGHTS: dict[str, dict[str, float]] = {
    "tutorial": {"practical_orientation": 0.9, "self_improvement": 0.5},
    "how-to": {"practical_orientation": 1.0, "self_improvement": 0.4},
    "productivity": {"self_improvement": 0.9, "practical_orientation": 0.5},
    "career": {"self_improvement": 0.8, "practical_orientation": 0.4},
    "news": {"social_awareness": 1.0, "intellectual_curiosity": 0.3},
    "politics": {"social_awareness": 0.9, "depth_immersion": 0.4},
    "documentary": {"depth_immersion": 0.8, "intellectual_curiosity": 0.6},
    "asmr": {"emotional_comfort": 1.0},
    "music": {"emotional_comfort": 0.7, "entertainment_release": 0.4},
    "healing": {"emotional_comfort": 0.9},
    "variety": {"entertainment_release": 1.0},
    "meme": {"entertainment_release": 0.9, "creative_expression": 0.3},
    "gaming": {"entertainment_release": 0.7, "depth_immersion": 0.5},
    "shorts": {"entertainment_release": 0.6, "intellectual_curiosity": -0.2},
    "diy": {"creative_expression": 0.9, "practical_orientation": 0.4},
    "art": {"creative_expression": 1.0},
    "science": {"intellectual_curiosity": 0.9, "depth_immersion": 0.5},
    "philosophy": {"intellectual_curiosity": 0.7, "depth_immersion": 0.8},
    "vlog": {"social_awareness": 0.4, "entertainment_release": 0.5},
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def filter_watch_records(records: list[IndexedRecord]) -> list[IndexedRecord]:
    return [r for r in records if r.source_type == "watch"]


def filter_search_records(records: list[IndexedRecord]) -> list[IndexedRecord]:
    return [r for r in records if r.source_type == "search"]


def get_channel_breakdown(records: list[IndexedRecord]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for record in filter_watch_records(records):
        channel = record.channel or "unknown"
        breakdown[channel] = breakdown.get(channel, 0) + (record.duration_sec or 0)
    return dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))


def get_search_queries(records: list[IndexedRecord]) -> list[str]:
    return [r.query for r in filter_search_records(records) if r.query]


def get_tag_distribution(records: list[IndexedRecord]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.tags)
    return dict(counter.most_common())


def get_sample_records(
    records: list[IndexedRecord], limit: int = 8
) -> list[IndexedRecord]:
    watches = filter_watch_records(records)[: max(1, limit // 2)]
    searches = filter_search_records(records)[: max(1, limit // 2)]
    return (watches + searches)[:limit]


def compute_search_active_ratio(records: list[IndexedRecord]) -> float:
    total = len(records) or 1
    return round(len(filter_search_records(records)) / total, 3)


def compute_viewing_concentration(records: list[IndexedRecord]) -> float:
    channel_breakdown = get_channel_breakdown(records)
    if not channel_breakdown:
        return 0.0
    total_watch_sec = sum(channel_breakdown.values()) or 1
    top_channel_sec = max(channel_breakdown.values())
    concentration = top_channel_sec / total_watch_sec
    unique_channels = len(channel_breakdown)
    channel_factor = 1.0 / max(unique_channels, 1)
    return round(_clamp_unit(concentration * 0.7 + channel_factor * 0.3), 3)


def _norm_ratio(value: float, norm: float) -> float:
    if norm <= 0:
        return 0.0
    return _clamp_unit(value / norm)


def trail_from_search(
    search: IndexedRecord, watches: list[IndexedRecord]
) -> list[IndexedRecord]:
    if search.recorded_at is None:
        return []
    after = [
        watch
        for watch in watches
        if watch.recorded_at
        and watch.recorded_at > search.recorded_at
        and watch.channel
    ]
    min_dt = datetime.min.replace(tzinfo=UTC)
    after.sort(key=lambda record: record.recorded_at or min_dt)

    anchor: str | None = None
    trail: list[IndexedRecord] = []
    for watch in after:
        if anchor is None:
            anchor = watch.channel
            trail.append(watch)
            continue
        if watch.channel != anchor:
            continue
        last_at = trail[-1].recorded_at
        if last_at is None or watch.recorded_at is None:
            continue
        gap_hours = (watch.recorded_at - last_at).total_seconds() / 3600
        if gap_hours <= EXPLORATION_CHAIN_GAP_HOURS:
            trail.append(watch)
    return trail


def _thread_score(trail: list[IndexedRecord]) -> float:
    if not trail:
        return 0.0
    total_duration = sum(record.duration_sec or 0 for record in trail)
    count = len(trail)
    return 0.6 * _norm_ratio(
        total_duration, EXPLORATION_DURATION_NORM_SEC
    ) + 0.4 * _norm_ratio(count, EXPLORATION_COUNT_NORM)


def compute_exploration_depth(records: list[IndexedRecord]) -> float:
    searches = [r for r in filter_search_records(records) if r.recorded_at]
    if not searches:
        return 0.0
    watches = filter_watch_records(records)
    scores = [_thread_score(trail_from_search(search, watches)) for search in searches]
    return round(sum(scores) / len(scores), 3)


def compute_taste_diversity_index(axes: Synapse8Axes) -> float:
    values = [float(getattr(axes, key)) for key in TASTE_DIVERSITY_AXES]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = variance**0.5
    return round(_clamp(100 - std * 2.5), 1)


def compute_layer_b_habits(records: list[IndexedRecord]) -> LayerB:
    return LayerB(
        search_active_ratio=compute_search_active_ratio(records),
        viewing_concentration=compute_viewing_concentration(records),
        taste_diversity_index=0.0,
        exploration_depth=compute_exploration_depth(records),
    )


def complete_layer_b(partial: LayerB, axes: Synapse8Axes) -> LayerB:
    return LayerB(
        search_active_ratio=partial.search_active_ratio,
        viewing_concentration=partial.viewing_concentration,
        taste_diversity_index=compute_taste_diversity_index(axes),
        exploration_depth=partial.exploration_depth,
    )


def top_axes(axes: Synapse8Axes, count: int = 2) -> list[str]:
    axis_values = [getattr(axes, key) for key in SYNAPSE_AXIS_KEYS]
    ranked = sorted(
        zip(SYNAPSE_AXIS_KEYS, axis_values, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    return [key for key, _ in ranked[:count]]


def _score_from_tags(records: list[IndexedRecord]) -> dict[str, float]:
    scores = {key: 35.0 for key in SYNAPSE_AXIS_KEYS}
    for record in records:
        weight = 2.0 if record.source_type == "watch" else 1.2
        if record.is_shorts:
            weight *= 0.8
        for tag in record.tags:
            for axis, delta in TAG_AXIS_WEIGHTS.get(tag, {}).items():
                scores[axis] = scores.get(axis, 35.0) + delta * 8 * weight

    watches = filter_watch_records(records)
    if watches:
        avg_duration = sum(r.duration_sec or 0 for r in watches) / len(watches)
        if avg_duration >= 900:
            scores["depth_immersion"] += 15
        elif avg_duration >= 600:
            scores["depth_immersion"] += 8
        shorts_ratio = sum(1 for r in watches if r.is_shorts) / len(watches)
        scores["entertainment_release"] += shorts_ratio * 20
        scores["depth_immersion"] -= shorts_ratio * 12

    searches = filter_search_records(records)
    unique_queries = len(set(get_search_queries(records)))
    scores["intellectual_curiosity"] += min(unique_queries, 8) * 2
    scores["practical_orientation"] += min(len(searches), 6) * 1.5

    return {key: _clamp(scores[key]) for key in SYNAPSE_AXIS_KEYS}


def _build_top5_from_records(records: list[IndexedRecord]) -> list[Top5Interest]:
    label_scores: Counter[str] = Counter()
    evidence_map: dict[str, list[str]] = {}

    for record in records:
        if record.source_type == "watch" and record.channel:
            label = record.channel
            label_scores[label] += record.duration_sec or 60
            evidence_map.setdefault(label, [])
            if record.title and len(evidence_map[label]) < 2:
                evidence_map[label].append(record.title)
        elif record.source_type == "search" and record.query:
            label = f"검색: {record.query}"
            label_scores[label] += 30
            evidence_map.setdefault(label, [record.query])
        elif record.source_type == "scrap" and record.title:
            label = f"스크랩: {record.title}"
            label_scores[label] += 25
            evidence_map.setdefault(label, [])
            if len(evidence_map[label]) < 2:
                evidence_map[label].append(record.title)

    top_items = label_scores.most_common(5)
    max_score = top_items[0][1] if top_items else 1
    return [
        Top5Interest(
            rank=idx,
            label=label,
            score=round(score / max_score, 3),
            evidence=evidence_map.get(label, [])[:2],
        )
        for idx, (label, score) in enumerate(top_items, start=1)
    ]


def fallback_analysis(
    user_id: str,
    records: list[IndexedRecord],
    layer_b: LayerB,
    investigation_log: list[str],
) -> ProfilerAnalysisOutput:
    scores = _score_from_tags(records)
    if layer_b.viewing_concentration > 0.65:
        scores["social_awareness"] = _clamp(scores["social_awareness"] + 10)
        scores["intellectual_curiosity"] = _clamp(scores["intellectual_curiosity"] - 8)
    if layer_b.viewing_concentration > 0.55:
        scores["depth_immersion"] = _clamp(scores["depth_immersion"] + 6)

    axes = Synapse8Axes(**{key: int(round(scores[key])) for key in SYNAPSE_AXIS_KEYS})
    top5 = _build_top5_from_records(records)
    dominant = top_axes(axes)
    summary = (
        f"{user_id} 사용자는 {', '.join(dominant)} 성향이 "
        f"두드러지는 소비 패턴을 보입니다. "
        f"채널 편중도 {layer_b.viewing_concentration:.0%}, "
        f"검색 활동 {layer_b.search_active_ratio:.0%}, "
        f"탐색 깊이 {layer_b.exploration_depth:.0%}입니다. "
        f"(규칙 기반 분석 — Gemini API 키 미설정)"
    )
    axis_notes = {
        key: f"{key} 점수 {getattr(axes, key)} — 태그·시청 패턴 기반 추정"
        for key in SYNAPSE_AXIS_KEYS
    }
    investigation_log.append("fallback: rule-based axis scoring applied")
    return ProfilerAnalysisOutput(
        axes=axes,
        top5_interests=top5,
        summary=summary,
        axis_notes=axis_notes,
    )
