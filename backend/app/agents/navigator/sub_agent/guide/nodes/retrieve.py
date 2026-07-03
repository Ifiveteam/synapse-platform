"""retrieve 노드 — 심화(성향) RAG + 확장(도메인) 다리 검색.

심화: 성향 쿼리로 실제 시청 근거를 찾는다.
확장: 도메인 쿼리로 그 도메인에 가장 가까운 기존 시청(다리)을 찾되, 유사도 임계값
넘는 것만 채택한다(억지 연결 방지 — 없으면 순수 전방향으로).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.navigator.sub_agent.guide.constants import (
    BRIDGE_SIM_THRESHOLD,
    CATALOG_SEARCH_LIMIT,
    disposition_query,
    domain_query,
)
from app.agents.navigator.sub_agent.guide.schemas import CatalogHit
from app.agents.navigator.sub_agent.guide.state import GuideState
from app.agents.navigator.sub_agent.guide.store import get_store
from app.agents.shared.embedding import embed_texts

logger = logging.getLogger(__name__)


async def retrieve(state: GuideState, config: RunnableConfig) -> dict[str, Any]:
    store = get_store(config)
    relax = state.get("relax_level", 0)
    deepen = state["deepen_targets"]
    expand = state["expand_domains"]
    evidence: dict[str, list[CatalogHit]] = dict(state.get("evidence") or {})
    bridge: dict[str, list[CatalogHit]] = dict(state.get("bridge_evidence") or {})
    base = {
        "retrieve_attempts": state.get("retrieve_attempts", 0) + 1,
        "relax_level": relax + 1,
    }

    if store is None:
        return {"evidence": evidence, "bridge_evidence": bridge, **base}

    disp_queries = [disposition_query(a, relax) for a in deepen]
    dom_queries = [domain_query(d) for d in expand]
    try:
        vectors = await asyncio.to_thread(embed_texts, disp_queries + dom_queries)
    except Exception:
        logger.exception("guide retrieve: embedding failed")
        vectors = []
    if not vectors:
        return {"evidence": evidence, "bridge_evidence": bridge, **base}

    disp_vecs = vectors[: len(deepen)]
    dom_vecs = vectors[len(deepen) :]

    # 심화: 성향별 실시청 근거
    if disp_vecs:
        disp_res = await asyncio.gather(
            *(
                store.search_by_axis(state["user_id"], v, CATALOG_SEARCH_LIMIT)
                for v in disp_vecs
            ),
            return_exceptions=True,
        )
        for axis, res in zip(deepen, disp_res, strict=True):
            if isinstance(res, Exception):
                logger.warning("guide retrieve: deepen search failed axis=%s", axis)
                continue
            if res:
                evidence[axis] = res

    # 확장: 도메인 다리 (임계값 통과분만)
    if dom_vecs:
        dom_res = await asyncio.gather(
            *(
                store.search_by_axis(state["user_id"], v, CATALOG_SEARCH_LIMIT)
                for v in dom_vecs
            ),
            return_exceptions=True,
        )
        for domain, res in zip(expand, dom_res, strict=True):
            if isinstance(res, Exception):
                logger.warning("guide retrieve: bridge search failed domain=%s", domain)
                continue
            good = [h for h in res if h.similarity >= BRIDGE_SIM_THRESHOLD]
            if good:
                bridge[domain] = good

    return {"evidence": evidence, "bridge_evidence": bridge, **base}
