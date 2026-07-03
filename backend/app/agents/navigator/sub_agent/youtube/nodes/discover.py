"""discover 노드 — 이상향+시청기록으로 검색어 작문 → search?type=channel."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.navigator.llm import invoke_structured_safe
from app.agents.navigator.sub_agent.youtube.client import search_channels
from app.agents.navigator.sub_agent.youtube.constants import (
    CHANNELS_PER_QUERY,
    PROPOSE_TEMPERATURE,
    SEARCH_QUERIES_MAX,
)
from app.agents.navigator.sub_agent.youtube.prompts import build_query_prompt
from app.agents.navigator.sub_agent.youtube.schemas import QuerySpec, WatchGrounding
from app.agents.navigator.sub_agent.youtube.state import PlaylistState
from app.agents.navigator.sub_agent.youtube.store import get_store


async def discover(state: PlaylistState, config: RunnableConfig) -> dict[str, Any]:
    store = get_store(config)
    updates: dict[str, Any] = {}

    grounding = state.get("grounding")
    if grounding is None:
        grounding = (
            await store.fetch_watch_grounding(state["user_id"])
            if store
            else WatchGrounding()
        )
        updates["grounding"] = grounding
    if state.get("watched") is None:
        updates["watched"] = (
            await store.fetch_watched_video_ids(state["user_id"]) if store else set()
        )

    attempts = state.get("attempts", 0)
    spec = await invoke_structured_safe(
        system_instruction=build_query_prompt(
            persona_label=state["persona_label"],
            values13=state["values13"],
            reasoning=state["reasoning"],
            ideal_type=state["ideal_type"],
            grounding=grounding,
            current_interest=state.get("current_interest"),
            raise_domains=state.get("raise_domains"),
            broaden=attempts > 0,
        ),
        user_content="채널 검색어를 만드세요.",
        schema=QuerySpec,
        temperature=PROPOSE_TEMPERATURE,
    )
    tried = list(state.get("tried_queries") or [])
    queries = [
        q for q in (spec.queries if spec else [])[:SEARCH_QUERIES_MAX] if q not in tried
    ]

    results = await asyncio.gather(
        *(search_channels(query=q, max_results=CHANNELS_PER_QUERY) for q in queries)
    )
    found = list(state.get("found_channels") or [])
    seen = {c.channel_id for c in found}
    for res in results:
        for ch in res:
            if ch.channel_id not in seen:
                found.append(ch)
                seen.add(ch.channel_id)

    updates.update(
        {
            "queries": queries,
            "tried_queries": tried + queries,
            "found_channels": found,
            "attempts": attempts + 1,
        }
    )
    return updates
