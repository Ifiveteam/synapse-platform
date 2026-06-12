"""Record aggregation helpers and LangChain investigation tools."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime

from langchain_core.tools import StructuredTool

from app.agents.profiler.base import IndexedRecord

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

INVESTIGATION_TOOL_NAMES: tuple[str, ...] = (
    "get_channel_breakdown",
    "get_search_queries",
    "get_tag_distribution",
    "get_sample_records",
)


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


def trail_from_search(
    search: IndexedRecord, watches: list[IndexedRecord], *, gap_hours: float = 24
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
        if (watch.recorded_at - last_at).total_seconds() / 3600 <= gap_hours:
            trail.append(watch)
    return trail


def build_investigation_tools(records: list[IndexedRecord]) -> list[StructuredTool]:
    """Bind investigation tools to the current user's indexed records."""

    def channel_breakdown() -> str:
        return json.dumps(get_channel_breakdown(records), ensure_ascii=False)

    def search_queries() -> str:
        return json.dumps(get_search_queries(records), ensure_ascii=False)

    def tag_distribution() -> str:
        return json.dumps(get_tag_distribution(records), ensure_ascii=False)

    def sample_records() -> str:
        samples = get_sample_records(records)
        payload = [
            {
                "source_type": r.source_type,
                "title": r.title,
                "query": r.query,
                "channel": r.channel,
                "tags": r.tags,
                "duration_sec": r.duration_sec,
            }
            for r in samples
        ]
        return json.dumps(payload, ensure_ascii=False)

    return [
        StructuredTool.from_function(
            func=channel_breakdown,
            name="get_channel_breakdown",
            description="시청 기록을 채널별 시청 시간(초)으로 집계합니다.",
        ),
        StructuredTool.from_function(
            func=search_queries,
            name="get_search_queries",
            description="사용자의 검색어 목록을 반환합니다.",
        ),
        StructuredTool.from_function(
            func=tag_distribution,
            name="get_tag_distribution",
            description="Indexer가 부여한 taxonomy 태그의 빈도 분포를 반환합니다.",
        ),
        StructuredTool.from_function(
            func=sample_records,
            name="get_sample_records",
            description="분석에 참고할 대표 시청·검색 레코드 샘플을 반환합니다.",
        ),
    ]
