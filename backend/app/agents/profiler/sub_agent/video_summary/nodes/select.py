"""catalog 영상 선별 + 자막 fetch."""

from __future__ import annotations

import asyncio
import logging

from app.agents.profiler.sub_agent.video_summary.state import (
    CatalogInput,
    VideoSummaryState,
)
from app.agents.profiler.sub_agent.video_summary.transcript import (
    fetch_youtube_transcript,
)

logger = logging.getLogger(__name__)

_CONCURRENCY = 4


def _row_to_catalog(row) -> CatalogInput:
    return {
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


def _rows_to_catalogs(rows) -> list[CatalogInput]:
    return [_row_to_catalog(row) for row in rows]


async def _fetch_transcripts(catalogs: list[CatalogInput]) -> list[CatalogInput]:
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _one(catalog: CatalogInput) -> tuple[CatalogInput, str]:
        async with sem:
            result = await asyncio.to_thread(
                fetch_youtube_transcript, catalog.get("url")
            )
        return {**catalog, "transcript": result.text}, result.status

    pairs = await asyncio.gather(*[_one(c) for c in catalogs])
    if not pairs:
        return []

    statuses = [status for _, status in pairs]
    ok = statuses.count("ok")
    none = statuses.count("none")
    blocked = statuses.count("blocked")
    logger.info(
        "[select] 자막 fetch — 성공 %d / 없음 %d / 실패(차단의심) %d (총 %d)",
        ok,
        none,
        blocked,
        len(statuses),
    )
    # 실패가 절반 이상이거나 다수면 차단 가능성 경고 (가시성)
    if blocked and blocked >= max(3, len(statuses) // 2):
        logger.warning(
            "[select] 자막 실패율 높음 (%d/%d) — YouTube rate limit/IP 차단 가능성",
            blocked,
            len(statuses),
        )
    return [catalog for catalog, _ in pairs]


async def node_select(state: VideoSummaryState) -> VideoSummaryState:
    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import (
            fetch_analysis_for_catalog_ids,
            fetch_catalog_rows,
            fetch_unanalyzed_catalog,
        )
        from app.services.profiler.sampling import select_analysis_sample

        # 숏폼은 자막이 거의 없어 fetch 안 함 — 제목·설명·태그로만 분석.
        async with AsyncSessionLocal() as session:
            if state.get("limit") is not None:
                rows = await fetch_unanalyzed_catalog(
                    session, state["user_id"], state.get("limit")
                )
            else:
                catalog_rows = await fetch_catalog_rows(session, state["user_id"])
                rows = select_analysis_sample(catalog_rows)

            long_rows = [r for r in rows if not r.is_shorts]
            short_rows = [r for r in rows if r.is_shorts]

            # 이미 분석돼 transcript가 저장된 롱폼은 재사용 → 자막 재호출↓ (차단·비용·속도)
            existing = await fetch_analysis_for_catalog_ids(
                session, [r.id for r in long_rows]
            )
            cached = {
                a.catalog_id: a.transcript
                for a in existing
                if (a.transcript or "").strip()
            }

        cached_rows = [r for r in long_rows if r.id in cached]
        fetch_rows = [r for r in long_rows if r.id not in cached]

        cached_catalogs = [
            {**_row_to_catalog(r), "transcript": cached[r.id]} for r in cached_rows
        ]
        if cached_catalogs:
            logger.info("[select] 자막 재사용 %d건 (재호출 생략)", len(cached_catalogs))
        fetched_catalogs = await _fetch_transcripts(_rows_to_catalogs(fetch_rows))
        short_catalogs = _rows_to_catalogs(short_rows)
        catalogs = cached_catalogs + fetched_catalogs + short_catalogs
        return {**state, "catalogs": catalogs, "error": None}
    except Exception as e:
        return {**state, "catalogs": [], "error": str(e)}
