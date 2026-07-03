"""curate 노드 — (임베딩 프리랭크) + LLM 최종 선택+이유 → 재생목록 10개."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agents.navigator.llm import invoke_structured_safe
from app.agents.navigator.schemas import Playlist, PlaylistItem
from app.agents.navigator.sub_agent.youtube.constants import (
    CURATE_TEMPERATURE,
    MAX_ITEMS_TOTAL,
    PRERANK_POOL,
)
from app.agents.navigator.sub_agent.youtube.prompts import build_curate_prompt
from app.agents.navigator.sub_agent.youtube.schemas import PlaylistCuration
from app.agents.navigator.sub_agent.youtube.state import PlaylistState
from app.agents.shared.embedding import embed_texts

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


async def _prerank(
    items: list[PlaylistItem], persona_text: str, k: int
) -> list[PlaylistItem]:
    """페르소나 설명 vs 영상 제목 cosine 상위 k. 실패 시 앞 k개."""
    try:
        vectors = await asyncio.to_thread(
            embed_texts, [persona_text, *[v.title for v in items]]
        )
        pvec, tvecs = vectors[0], vectors[1:]
        scored = sorted(
            zip(items, tvecs, strict=True),
            key=lambda it: _cosine(pvec, it[1]),
            reverse=True,
        )
        return [it for it, _ in scored[:k]]
    except Exception:
        logger.warning("playlist curate prerank failed — fallback to head")
        return items[:k]


async def curate(state: PlaylistState) -> dict[str, Any]:
    candidates = state.get("candidates") or []
    persona_label = state["persona_label"]
    reasoning = state["reasoning"]

    if not candidates:
        return {"result": Playlist(summary="추천할 영상을 찾지 못했습니다.", items=[])}

    pool = candidates
    if len(pool) > PRERANK_POOL:
        pool = await _prerank(pool, f"{persona_label} {reasoning}", PRERANK_POOL)

    res = await invoke_structured_safe(
        system_instruction=build_curate_prompt(
            persona_label=persona_label,
            reasoning=reasoning,
            candidates=pool,
            raise_domains=state.get("raise_domains"),
        ),
        user_content="재생목록을 구성하세요.",
        schema=PlaylistCuration,
        temperature=CURATE_TEMPERATURE,
    )

    items: list[PlaylistItem] = []
    used: set[str] = set()
    if res:
        for p in res.picks:
            if 0 <= p.index < len(pool) and pool[p.index].video_id not in used:
                items.append(pool[p.index].model_copy(update={"reason": p.reason}))
                used.add(pool[p.index].video_id)
            if len(items) >= MAX_ITEMS_TOTAL:
                break

    # 폴백: 부족하면 풀 상위로 채움
    for v in pool:
        if len(items) >= MAX_ITEMS_TOTAL:
            break
        if v.video_id not in used:
            items.append(v)
            used.add(v.video_id)

    summary = (res.summary if res else "") or f"{persona_label}에 맞춘 추천 재생목록"
    return {"result": Playlist(summary=summary, items=items[:MAX_ITEMS_TOTAL])}
