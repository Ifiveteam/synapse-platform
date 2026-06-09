"""Investigation evidence helpers for the profiler agent (tool loop + structured)."""

from __future__ import annotations

import json

from app.agents.profiler.base import IndexedRecord
from app.agents.profiler.subagent.scoring import (
    get_channel_breakdown,
    get_sample_records,
    get_search_queries,
    get_tag_distribution,
)

TOOL_TO_EVIDENCE_KEY: dict[str, str] = {
    "get_channel_breakdown": "channel_breakdown",
    "get_search_queries": "search_queries",
    "get_tag_distribution": "tag_distribution",
    "get_sample_records": "sample_records",
}

MAX_CHANNELS = 10
MAX_TAGS = 15
MAX_QUERIES = 10
MAX_SAMPLES = 6


def _sample_payload(records: list[IndexedRecord]) -> list[dict[str, object]]:
    return [
        {
            "source_type": record.source_type,
            "title": record.title,
            "query": record.query,
            "channel": record.channel,
            "tags": record.tags,
            "duration_sec": record.duration_sec,
        }
        for record in records
    ]


def build_investigation_evidence(records: list[IndexedRecord]) -> dict[str, object]:
    channels = get_channel_breakdown(records)
    tags = get_tag_distribution(records)
    return {
        "channel_breakdown": dict(list(channels.items())[:MAX_CHANNELS]),
        "search_queries": get_search_queries(records)[:MAX_QUERIES],
        "tag_distribution": dict(list(tags.items())[:MAX_TAGS]),
        "sample_records": _sample_payload(get_sample_records(records, MAX_SAMPLES)),
    }


def merge_tool_results(
    base: dict[str, object],
    tool_results: dict[str, str],
) -> dict[str, object]:
    merged = dict(base)
    for tool_name, content in tool_results.items():
        key = TOOL_TO_EVIDENCE_KEY.get(tool_name)
        if key is None:
            continue
        try:
            merged[key] = json.loads(content)
        except json.JSONDecodeError:
            continue
    return cap_investigation_evidence(merged)


def cap_investigation_evidence(evidence: dict[str, object]) -> dict[str, object]:
    capped = dict(evidence)
    channels = capped.get("channel_breakdown")
    if isinstance(channels, dict):
        capped["channel_breakdown"] = dict(list(channels.items())[:MAX_CHANNELS])

    tags = capped.get("tag_distribution")
    if isinstance(tags, dict):
        capped["tag_distribution"] = dict(list(tags.items())[:MAX_TAGS])

    queries = capped.get("search_queries")
    if isinstance(queries, list):
        capped["search_queries"] = queries[:MAX_QUERIES]

    samples = capped.get("sample_records")
    if isinstance(samples, list):
        capped["sample_records"] = samples[:MAX_SAMPLES]

    return capped


def evidence_json_sections(evidence: dict[str, object]) -> dict[str, str]:
    return {
        key: json.dumps(evidence.get(key, {}), ensure_ascii=False, indent=2)
        for key in (
            "channel_breakdown",
            "search_queries",
            "tag_distribution",
            "sample_records",
        )
    }
