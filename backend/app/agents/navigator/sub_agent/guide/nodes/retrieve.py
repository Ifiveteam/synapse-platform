"""retrieve 노드 — 약한 축을 임베딩해 catalog에서 실제 시청 근거를 RAG 검색."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.navigator.sub_agent.guide.constants import (
    CATALOG_SEARCH_LIMIT,
    axis_query,
)
from app.agents.navigator.sub_agent.guide.state import GuideState
from app.agents.navigator.sub_agent.guide.store import CatalogHit, get_store
from app.agents.shared.embedding import embed_texts

logger = logging.getLogger(__name__)


async def retrieve(state: GuideState, config: RunnableConfig) -> dict[str, Any]:
    store = get_store(config)
    weak_axes = state["weak_axes"]
    relax = state.get("relax_level", 0)
    evidence: dict[str, list[CatalogHit]] = dict(state.get("evidence") or {})
    base = {
        "retrieve_attempts": state.get("retrieve_attempts", 0) + 1,
        "relax_level": relax + 1,
    }

    if store is None:
        return {"evidence": evidence, **base}

    queries = [axis_query(axis, relax) for axis in weak_axes]
    try:
        vectors = await asyncio.to_thread(embed_texts, queries)
    except Exception:
        logger.exception("guide retrieve: embedding failed")
        vectors = []

    if not vectors:
        return {"evidence": evidence, **base}

    results = await asyncio.gather(
        *(
            store.search_by_axis(state["user_id"], vec, CATALOG_SEARCH_LIMIT)
            for vec in vectors
        ),
        return_exceptions=True,
    )
    for axis, res in zip(weak_axes, results, strict=True):
        if isinstance(res, Exception):
            logger.warning("guide retrieve: search failed axis=%s", axis)
            continue
        if res:  # 찾은 경우에만 갱신 (재검색 시 이전 근거 유지)
            evidence[axis] = res

    return {"evidence": evidence, **base}
