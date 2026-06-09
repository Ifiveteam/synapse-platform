from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.agents.profiler.base import BehaviorPatterns, IndexedRecord
from app.agents.profiler.subagent.scoring import filter_watch_records

_HOUR_BUCKETS = ("morning", "afternoon", "evening", "night")


def _hour_bucket(dt: datetime) -> str:
    hour = dt.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def compute_behavior_patterns(records: list[IndexedRecord]) -> BehaviorPatterns:
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

    top_channels = [
        {"channel": name, "count": count}
        for name, count in channel_repeat.most_common(5)
    ]
    top_tags = [
        {"tag": name, "count": count} for name, count in tag_counts.most_common(8)
    ]

    return BehaviorPatterns(
        hour_distribution=hour_distribution,
        weekend_ratio=weekend_ratio,
        top_repeated_channels=top_channels,
        top_repeated_tags=top_tags,
    )
