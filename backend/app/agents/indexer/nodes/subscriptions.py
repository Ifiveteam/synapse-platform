"""노드: 구독정보 전체 교체 (ZIP에 구독 CSV 있을 때만)."""

from __future__ import annotations

import logging

from app.agents.indexer.state import IndexerState

logger = logging.getLogger(__name__)


async def node_save_subscriptions(state: IndexerState) -> IndexerState:
    """구독 CSV가 있던 경우에만 전체 교체. 없으면 기존 구독 유지(no-op)."""
    if not state.get("subscription_file_found"):
        return {**state, "subscription_saved": 0}

    user_id = state.get("user_id")
    if user_id is None:
        logger.warning("[save_subscriptions] user_id 없음 → 스킵")
        return {**state, "subscription_saved": 0}

    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import replace_subscriptions

        rows = state.get("subscriptions") or []
        async with AsyncSessionLocal() as session:
            saved = await replace_subscriptions(session, user_id, rows)
            await session.commit()
        logger.info(f"[save_subscriptions] 구독 {saved}건 전체 교체")
        return {**state, "subscription_saved": saved}
    except Exception as e:
        # 구독 저장 실패가 시청기록 적재(주 결과)를 무효화하지 않도록 error 전파 안 함
        logger.warning(f"[save_subscriptions] 실패: {e}", exc_info=True)
        return {**state, "subscription_saved": 0}
