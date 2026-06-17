"""catalog 영상 선별 + 자막 fetch."""

from __future__ import annotations

import asyncio

from app.agents.profiler.sub_agent.video_summary.state import (
    CatalogInput,
    VideoSummaryState,
)
from app.agents.profiler.sub_agent.video_summary.tool import fetch_youtube_transcript

_CONCURRENCY = 4


def _rows_to_catalogs(rows) -> list[CatalogInput]:
    return [
        {
            "catalog_id": row.id,
            "user_id": row.user_id,
            "url": row.url,
            "title": row.title,
            "channel": row.channel,
            "description": row.description,
            "transcript": None,
            "tags": row.tags if isinstance(row.tags, list) else None,
            "youtube_category_id": row.youtube_category_id,
            "thumbnail_url": row.thumbnail_url,
        }
        for row in rows
    ]


async def _fetch_transcripts(catalogs: list[CatalogInput]) -> list[CatalogInput]:
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _one(catalog: CatalogInput) -> CatalogInput:
        async with sem:
            transcript = await asyncio.to_thread(
                fetch_youtube_transcript, catalog.get("url")
            )
        return {**catalog, "transcript": transcript}

    return list(await asyncio.gather(*[_one(c) for c in catalogs]))


async def node_select(state: VideoSummaryState) -> VideoSummaryState:
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import (
            fetch_catalog_rows,
            fetch_unanalyzed_catalog,
        )
        from app.services.profiler.sampling import select_analysis_sample

        async with AsyncSessionLocal() as session:
            if state.get("limit") is not None:
                rows = await fetch_unanalyzed_catalog(
                    session, state["user_id"], state.get("limit")
                )
            else:
                catalog_rows = await fetch_catalog_rows(session, state["user_id"])
                rows = select_analysis_sample(catalog_rows)

        catalogs = await _fetch_transcripts(_rows_to_catalogs(rows))
        return {**state, "catalogs": catalogs, "error": None}
    except Exception as e:
        return {**state, "catalogs": [], "error": str(e)}
