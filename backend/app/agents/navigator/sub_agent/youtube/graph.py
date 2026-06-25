"""YouTube 재생목록 서브에이전트 그래프 — discover→pick→collect→evaluate(⇄discover)→curate."""

from __future__ import annotations

import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.schemas import Playlist
from app.agents.navigator.sub_agent.youtube.constants import RESERVOIR_TARGET
from app.agents.navigator.sub_agent.youtube.nodes import (
    collect,
    curate,
    discover,
    evaluate,
    pick,
)
from app.agents.navigator.sub_agent.youtube.state import PlaylistBuild, PlaylistState
from app.agents.navigator.sub_agent.youtube.store import PlaylistStore, build_run_config


def route_after_evaluate(state: PlaylistState) -> Literal["discover", "curate"]:
    return "discover" if state.get("decision") == "discover" else "curate"


_compiled = None


def build_playlist_graph():
    graph = StateGraph(PlaylistState)
    graph.add_node("discover", discover)
    graph.add_node("pick", pick)
    graph.add_node("collect", collect)
    graph.add_node("evaluate", evaluate)
    graph.add_node("curate", curate)
    graph.add_edge(START, "discover")
    graph.add_edge("discover", "pick")
    graph.add_edge("pick", "collect")
    graph.add_edge("collect", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"discover": "discover", "curate": "curate"},
    )
    graph.add_edge("curate", END)
    return graph.compile()


def _get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_playlist_graph()
    return _compiled


async def run_playlist(
    *,
    store: PlaylistStore | None,
    user_id: uuid.UUID,
    persona_label: str,
    values13: dict[str, float],
    ideal_type: str,
    reasoning: str,
) -> PlaylistBuild:
    """생성 루프 실행 → 보여줄 10개 + 저수지 + 발굴 채널."""
    initial: PlaylistState = {
        "user_id": user_id,
        "persona_label": persona_label,
        "values13": values13,
        "ideal_type": ideal_type,
        "reasoning": reasoning,
    }
    final = await _get_graph().ainvoke(initial, config=build_run_config(store))

    playlist = final.get("result") or Playlist(
        summary="추천할 영상을 찾지 못했습니다.", items=[]
    )
    candidates = final.get("candidates") or []
    item_ids = {it.video_id for it in playlist.items}
    reservoir = [c for c in candidates if c.video_id not in item_ids][:RESERVOIR_TARGET]
    channels = final.get("picked_channels") or final.get("found_channels") or []
    return PlaylistBuild(playlist=playlist, reservoir=reservoir, channels=channels)
