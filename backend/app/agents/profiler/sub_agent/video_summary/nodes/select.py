"""catalog 영상 선별 (메타데이터만 사용 — 자막 미수집)."""

from __future__ import annotations

from app.agents.profiler.sub_agent.video_summary.state import (
    CatalogInput,
    VideoSummaryState,
)


def _row_to_catalog(row) -> CatalogInput:
    return {
        "catalog_id": row.id,
        "user_id": row.user_id,
        "url": row.url,
        "title": row.title,
        "channel": row.channel,
        "description": row.description,
        "tags": row.tags if isinstance(row.tags, list) else None,
        "youtube_category_id": row.youtube_category_id,
        "thumbnail_url": row.thumbnail_url,
    }


def _rows_to_catalogs(rows) -> list[CatalogInput]:
    return [_row_to_catalog(row) for row in rows]


async def node_select(state: VideoSummaryState) -> VideoSummaryState:
    try:
        from app.agents.shared.analysis_window import WATCH_CATALOG_WINDOW_DAYS
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import (
            fetch_catalog_rows_by_sources,
            fetch_recent_catalog_rows,
            fetch_unanalyzed_catalog,
        )
        from app.services.profiler.sampling import select_analysis_sample

        source_ids = state.get("analysis_source_ids")
        async with AsyncSessionLocal() as session:
            if state.get("limit") is not None:
                rows = await fetch_unanalyzed_catalog(
                    session, state["user_id"], state.get("limit")
                )
            elif source_ids:
                # 배치 스코프: 그 파일들 소속 영상 합집합의 최근 2달에서 샘플링
                catalog_rows = await fetch_catalog_rows_by_sources(
                    session, state["user_id"], source_ids, WATCH_CATALOG_WINDOW_DAYS
                )
                rows = select_analysis_sample(catalog_rows)
            else:
                # 통합본: 최근 2달(WATCH_CATALOG_WINDOW_DAYS) 시청 기록만 샘플링 대상
                catalog_rows = await fetch_recent_catalog_rows(
                    session, state["user_id"], WATCH_CATALOG_WINDOW_DAYS
                )
                rows = select_analysis_sample(catalog_rows)

        return {**state, "catalogs": _rows_to_catalogs(rows), "error": None}
    except Exception as e:
        return {**state, "catalogs": [], "error": str(e)}
