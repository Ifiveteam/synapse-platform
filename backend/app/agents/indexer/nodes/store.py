"""catalog upsert."""

from app.agents.indexer.state import IndexerState


async def node_save_catalog(state: IndexerState) -> IndexerState:
    """cleaned_data → user_watch_catalog upsert."""
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.indexer_repository import upsert_catalog_records

        user_id = state.get("user_id")
        if user_id is None:
            return {**state, "error": "user_id is required for catalog save"}

        items = state.get("cleaned_data") or []
        async with AsyncSessionLocal() as session:
            saved = await upsert_catalog_records(session, user_id, items)
            await session.commit()
        print(f"[save_catalog] {saved}건 저장")
        return {**state, "saved_count": saved, "error": None}
    except Exception as e:
        return {**state, "saved_count": 0, "error": str(e)}
