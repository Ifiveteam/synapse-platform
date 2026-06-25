"""evaluate 노드 — 자기교정(규칙): 후보 충분? → curate / 부족 → discover 재발굴."""

from __future__ import annotations

from typing import Any

from app.agents.navigator.sub_agent.youtube.constants import (
    MAX_ATTEMPTS,
    MIN_VALID_CANDIDATES,
)
from app.agents.navigator.sub_agent.youtube.state import PlaylistState


async def evaluate(state: PlaylistState) -> dict[str, Any]:
    candidates = state.get("candidates") or []
    attempts = state.get("attempts", 0)

    if len(candidates) >= MIN_VALID_CANDIDATES:
        return {"decision": "curate"}
    if attempts < MAX_ATTEMPTS:
        return {"decision": "discover"}  # 검색어 넓혀 재발굴
    return {"decision": "curate"}  # 가진 만큼이라도
