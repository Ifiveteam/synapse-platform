"""노드: Takeout parse + filter + dedupe + 60일."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import (
    WATCH_CATALOG_WINDOW_DAYS,
    parse_takeout_json,
    parse_takeout_zip,
)
from app.agents.indexer.tool import (
    preprocess as filter_takeout_rows,
)


def _parse_watched_at(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def parse_takeout_file(path: str) -> list[dict]:
    if path.endswith(".zip"):
        return parse_takeout_zip(path)
    return parse_takeout_json(path)


def dedupe_by_url(items: list[dict]) -> list[dict]:
    """URL당 최신 watched_at 1건."""
    by_url: dict[str, dict] = {}
    for item in items:
        url = item.get("url")
        if not url:
            continue
        existing = by_url.get(url)
        if not existing or item.get("watched_at", "") > existing.get("watched_at", ""):
            by_url[url] = item
    return list(by_url.values())


def apply_watch_window(
    items: list[dict], window_days: int = WATCH_CATALOG_WINDOW_DAYS
) -> tuple[list[dict], str, str]:
    now = datetime.now(timezone.utc)
    if not items:
        start = (now - timedelta(days=window_days)).isoformat()
        return [], start, now.isoformat()

    dates = [
        _parse_watched_at(item["watched_at"])
        for item in items
        if item.get("watched_at")
    ]
    analysis_end = max(dates) if dates else now
    analysis_start = analysis_end - timedelta(days=window_days)

    filtered = [
        item
        for item in items
        if analysis_start
        <= _parse_watched_at(item.get("watched_at", ""))
        <= analysis_end
    ]
    filtered.sort(key=lambda x: x["watched_at"], reverse=True)
    return filtered, analysis_start.isoformat(), analysis_end.isoformat()


def run_preprocess(json_path: str) -> dict:
    """parse → filter → dedupe → 60일. DB 저장 전 in-memory."""
    raw_data = parse_takeout_file(json_path)
    cleaned = filter_takeout_rows(raw_data)
    for row in cleaned:
        row["platform"] = "youtube"
    deduped = dedupe_by_url(cleaned)
    windowed, analysis_start, analysis_end = apply_watch_window(deduped)

    return {
        "raw_data": raw_data,
        "cleaned_data": windowed,
        "filtered_count": len(windowed),
        "analysis_start": analysis_start,
        "analysis_end": analysis_end,
    }


def node_preprocess(state: IndexerState) -> IndexerState:
    """parse + 광고·URL 필터 + dedupe + 60일 (Takeout 기본 데이터)."""
    try:
        result = run_preprocess(state["json_path"])
        return {**state, **result, "error": None}
    except Exception as e:
        return {
            **state,
            "raw_data": [],
            "cleaned_data": [],
            "filtered_count": 0,
            "error": str(e),
        }
