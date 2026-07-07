"""catalog upsert."""

import logging

from app.agents.indexer.state import IndexerState

logger = logging.getLogger(__name__)


async def node_save_catalog(state: IndexerState) -> IndexerState:
    """신규는 전체 upsert, 기존은 watched_at·watch_count만 갱신 (증분)."""
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import (
            link_source_catalog,
            update_watch_meta,
            upsert_catalog_records,
        )

        user_id = state.get("user_id")
        if user_id is None:
            return {**state, "error": "user_id is required for catalog save"}

        new_items = state.get("cleaned_data") or []
        existing_items = state.get("existing_items") or []
        source_id = state.get("analysis_source_id")
        async with AsyncSessionLocal() as session:
            saved = await upsert_catalog_records(session, user_id, new_items)
            touched = await update_watch_meta(session, user_id, existing_items)
            # 이 파일에 든 영상 전부(신규+기존)를 소스에 소속시킴 — 배치 스코프용
            linked = await link_source_catalog(
                session,
                user_id,
                source_id,
                [it.get("url") for it in (new_items + existing_items)],
            )
            await session.commit()
        logger.info(
            f"[save_catalog] 신규 {saved}건 저장 · 기존 {touched}건 메타 갱신 "
            f"· 소속 {linked}건 기록"
        )
        return {
            **state,
            "saved_count": saved,
            "touched_count": touched,
            "error": None,
        }
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}
