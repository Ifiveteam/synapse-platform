"""collect 노드 — 선택 채널 RSS → 안 본 새 영상 후보 수집."""

from __future__ import annotations

import asyncio
from typing import Any

from app.agents.navigator.schemas import PlaylistItem
from app.agents.navigator.sub_agent.youtube.client import fetch_channel_uploads
from app.agents.navigator.sub_agent.youtube.constants import UPLOADS_PER_CHANNEL
from app.agents.navigator.sub_agent.youtube.state import PlaylistState


async def collect(state: PlaylistState) -> dict[str, Any]:
    picked = state.get("picked_channels") or []
    watched = state.get("watched") or set()
    candidates = list(state.get("candidates") or [])

    have_vids = {c.video_id for c in candidates}
    collected_ch = {c.channel_id for c in candidates}
    to_collect = [ch for ch in picked if ch.channel_id not in collected_ch]
    if not to_collect:
        return {"candidates": candidates}

    results = await asyncio.gather(
        *(
            fetch_channel_uploads(channel_id=ch.channel_id, limit=UPLOADS_PER_CHANNEL)
            for ch in to_collect
        )
    )
    for ch, vids in zip(to_collect, results, strict=True):
        for v in vids:
            if v.video_id in have_vids or v.video_id in watched:
                continue
            candidates.append(
                PlaylistItem(
                    video_id=v.video_id,
                    title=v.title,
                    channel=v.channel or ch.title,
                    channel_id=ch.channel_id,
                    thumbnail_url=v.thumbnail_url,
                )
            )
            have_vids.add(v.video_id)

    return {"candidates": candidates}
