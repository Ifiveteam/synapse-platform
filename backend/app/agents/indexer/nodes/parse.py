import time
from datetime import datetime, timedelta, timezone

from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import parse_takeout_json, parse_takeout_zip, preprocess

WINDOW_DAYS = 60


def _parse_watched_at(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def node_start(state: IndexerState) -> IndexerState:
    return {**state, "started_at": time.time()}


def node_parse(state: IndexerState) -> IndexerState:
    try:
        path = state["json_path"]
        raw_data = (
            parse_takeout_zip(path)
            if path.endswith(".zip")
            else parse_takeout_json(path)
        )
        return {**state, "raw_data": raw_data, "error": None}
    except Exception as e:
        return {**state, "raw_data": [], "error": str(e)}


def node_preprocess(state: IndexerState) -> IndexerState:
    try:
        cleaned_data = preprocess(state["raw_data"])
        now = datetime.now(timezone.utc)

        if not cleaned_data:
            return {
                **state,
                "cleaned_data": [],
                "filtered_count": 0,
                "analysis_start": (now - timedelta(days=WINDOW_DAYS)).isoformat(),
                "analysis_end": now.isoformat(),
                "error": None,
            }

        dates = [
            _parse_watched_at(item["watched_at"])
            for item in cleaned_data
            if item.get("watched_at")
        ]
        analysis_end = max(dates) if dates else now
        analysis_start = analysis_end - timedelta(days=WINDOW_DAYS)

        filtered = [
            item
            for item in cleaned_data
            if analysis_start
            <= _parse_watched_at(item.get("watched_at", ""))
            <= analysis_end
        ]
        filtered.sort(key=lambda x: x["watched_at"], reverse=True)

        return {
            **state,
            "cleaned_data": filtered,
            "filtered_count": len(filtered),
            "analysis_start": analysis_start.isoformat(),
            "analysis_end": analysis_end.isoformat(),
            "error": None,
        }
    except Exception as e:
        return {**state, "cleaned_data": [], "filtered_count": 0, "error": str(e)}
