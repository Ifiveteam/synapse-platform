"""pick 노드 — 검색된 실재 채널 후보 중 페르소나 적합 채널 선택."""

from __future__ import annotations

from typing import Any

from app.agents.navigator.llm import invoke_structured_safe
from app.agents.navigator.sub_agent.youtube.constants import CURATED_CHANNELS
from app.agents.navigator.sub_agent.youtube.prompts import build_pick_prompt
from app.agents.navigator.sub_agent.youtube.schemas import ChannelPick
from app.agents.navigator.sub_agent.youtube.state import PlaylistState


async def pick(state: PlaylistState) -> dict[str, Any]:
    found = state.get("found_channels") or []
    if not found:
        return {"picked_channels": state.get("picked_channels") or []}

    res = await invoke_structured_safe(
        system_instruction=build_pick_prompt(
            persona_label=state["persona_label"],
            reasoning=state["reasoning"],
            channels=found,
        ),
        user_content="페르소나에 맞는 채널 인덱스를 고르세요.",
        schema=ChannelPick,
        temperature=0.2,
    )

    picked = list(state.get("picked_channels") or [])
    picked_ids = {c.channel_id for c in picked}
    if res:
        for idx in res.indices:
            if 0 <= idx < len(found) and found[idx].channel_id not in picked_ids:
                picked.append(found[idx])
                picked_ids.add(found[idx].channel_id)

    # 폴백: 선택이 비면 상위 채널로 채움
    if not picked:
        picked = found[:CURATED_CHANNELS]

    return {"picked_channels": picked[:CURATED_CHANNELS]}
