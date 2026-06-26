"""노드: 증분 분류 — 이미 인덱싱된 영상은 enrich/embed에서 제외.

신규(url 없음/임베딩 미완성) → 전체 처리(enrich+embed).
기존(임베딩 완료)           → watched_at·watch_count만 갱신 (save 단계).
"""

from __future__ import annotations

import logging

from app.agents.indexer.state import IndexerState

logger = logging.getLogger(__name__)


async def node_diff(state: IndexerState) -> IndexerState:
    """cleaned_data를 신규/기존으로 가른다."""
    try:
        user_id = state.get("user_id")
        items = state.get("cleaned_data") or []

        # user_id 없거나(스크립트) 입력 없음 → 전부 신규로 통과
        if user_id is None or not items:
            return {**state, "existing_items": [], "skipped_existing": 0, "error": None}

        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import fetch_indexed_urls

        async with AsyncSessionLocal() as session:
            indexed = await fetch_indexed_urls(session, user_id)

        new_items = [it for it in items if it.get("url") not in indexed]
        existing_items = [it for it in items if it.get("url") in indexed]

        logger.info(
            f"[diff] 신규 {len(new_items)}건 처리 · 기존 {len(existing_items)}건 "
            f"skip(메타만 갱신)"
        )
        return {
            **state,
            "cleaned_data": new_items,
            "existing_items": existing_items,
            "skipped_existing": len(existing_items),
            "error": None,
        }
    except Exception as e:
        return {**state, "error": str(e)}
