import time
from datetime import datetime, timedelta, timezone

from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import parse_takeout_json, parse_takeout_zip, preprocess


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
        cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cleaned_data = [
            item for item in cleaned_data if item.get("watched_at", "") >= cutoff
        ]
        filtered_count = len(cleaned_data)
        cleaned_data.sort(key=lambda x: x["watched_at"], reverse=True)
        cleaned_data = cleaned_data[:2000]
        return {
            **state,
            "cleaned_data": cleaned_data,
            "filtered_count": filtered_count,
            "error": None,
        }
    except Exception as e:
        return {**state, "cleaned_data": [], "filtered_count": 0, "error": str(e)}
