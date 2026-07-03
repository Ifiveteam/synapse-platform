"""YouTube 재생목록 서브에이전트 그래프 — discover→pick→collect→evaluate(⇄discover)→curate."""

from __future__ import annotations

import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.constants import INTEREST_DOMAINS
from app.agents.navigator.schemas import Playlist
from app.agents.navigator.sub_agent.youtube.constants import (
    RAISE_DOMAINS_TOP_K,
    RESERVOIR_TARGET,
)
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


def _raise_domains(
    current_interest: dict[str, float], target_interest: dict[str, float]
) -> list[str]:
    """target − current > 0 인 도메인을 갭 큰 순 top-K (새로 넓힐 것)."""
    gaps = {
        d: float(target_interest.get(d, 0.0)) - float(current_interest.get(d, 0.0))
        for d in INTEREST_DOMAINS
    }
    positive = sorted(
        [(d, g) for d, g in gaps.items() if g > 0], key=lambda x: x[1], reverse=True
    )
    return [d for d, _ in positive[:RAISE_DOMAINS_TOP_K]]


async def run_playlist(
    *,
    store: PlaylistStore | None,
    user_id: uuid.UUID,
    persona_label: str,
    values13: dict[str, float],
    ideal_type: str,
    reasoning: str,
    current_interest: dict[str, float] | None = None,
    target_interest: dict[str, float] | None = None,
    target_disposition: dict[str, float] | None = None,
) -> PlaylistBuild:
    """생성 루프 실행 → 보여줄 10개 + 저수지 + 발굴 채널."""
    current_interest = current_interest or {}
    initial: PlaylistState = {
        "user_id": user_id,
        "persona_label": persona_label,
        "values13": values13,
        "ideal_type": ideal_type,
        "reasoning": reasoning,
        "current_interest": current_interest,
        "raise_domains": _raise_domains(current_interest, target_interest or {}),
        "target_disposition": target_disposition or {},
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
