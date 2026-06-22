"""retrieve 노드 — 프로필 + 시청기록 + 영상분석 벡터 검색."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.constants import ANALYSIS_SEARCH_LIMIT, VIDEO_SEARCH_LIMIT
from app.agents.curator.types import CuratorState
from app.agents.shared.embedding import embed_texts

logger = logging.getLogger(__name__)


def _latest_user_message(state: CuratorState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    return ""


def _format_profile(profile) -> str:
    if not profile:
        return ""
    parts = []
    if profile.persona_label:
        parts.append(f"페르소나: {profile.persona_label}")
    if profile.summary_text:
        parts.append(f"요약: {profile.summary_text}")
    if profile.dominant_traits:
        parts.append(f"주요 특성: {profile.dominant_traits}")
    return "\n".join(parts)


async def _fetch_catalog_stats(db: AsyncSession, user_id) -> str:
    from sqlalchemy import func, select, text

    from app.models.user_watch_catalog import UserWatchCatalog

    total_q = await db.execute(
        select(func.count()).where(UserWatchCatalog.user_id == user_id)
    )
    total = total_q.scalar() or 0

    shorts_q = await db.execute(
        select(func.count()).where(
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.is_shorts.is_(True),
        )
    )
    shorts = shorts_q.scalar() or 0

    cat_q = await db.execute(
        select(UserWatchCatalog.youtube_category_id, func.count())
        .where(UserWatchCatalog.user_id == user_id)
        .group_by(UserWatchCatalog.youtube_category_id)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_cats = [f"{r[0] or '미분류'}({r[1]}건)" for r in cat_q.all()]

    return (
        f"총 시청 영상: {total}개 / 쇼츠 비율: {shorts}/{total} / "
        f"주요 카테고리: {', '.join(top_cats)}"
    )


async def _vector_search_catalog(db: AsyncSession, user_id, vec: list[float]) -> list[str]:
    from sqlalchemy import text

    rows = (await db.execute(
        text("""
            SELECT title, channel, youtube_category_id,
                   1 - (embedding <=> CAST(:vec AS vector)) AS score
            FROM user_watch_catalog
            WHERE user_id = :uid AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :lim
        """),
        {"vec": str(vec), "uid": str(user_id), "lim": VIDEO_SEARCH_LIMIT},
    )).fetchall()
    return [f"· {r.title} ({r.channel})" for r in rows]


async def _vector_search_analysis(db: AsyncSession, user_id, vec: list[float]) -> list[str]:
    from sqlalchemy import text

    rows = (await db.execute(
        text("""
            SELECT va.summary_kr,
                   1 - (va.embedding <=> CAST(:vec AS vector)) AS score
            FROM video_analysis va
            JOIN user_watch_catalog uwc ON va.catalog_id = uwc.id
            WHERE uwc.user_id = :uid AND va.embedding IS NOT NULL
            ORDER BY va.embedding <=> CAST(:vec AS vector)
            LIMIT :lim
        """),
        {"vec": str(vec), "uid": str(user_id), "lim": ANALYSIS_SEARCH_LIMIT},
    )).fetchall()
    return [f"· {r.summary_kr}" for r in rows]


async def retrieve(state: CuratorState, db: AsyncSession) -> dict[str, Any]:
    writer = get_stream_writer()
    writer({"event": "status", "content": "🔍 데이터를 검색하고 있습니다..."})

    user_id = state["user_id"]
    question = _latest_user_message(state)
    context_parts: list[str] = []

    # 1. 프로필 스냅샷
    try:
        from app.repositories.profiler_repository import fetch_latest_profile
        profile = await fetch_latest_profile(db, user_id)
        if profile:
            context_parts.append("[프로필]\n" + _format_profile(profile))
    except Exception as e:
        logger.warning("profile fetch failed: %s", e)

    # 2. 시청 통계
    try:
        stats = await _fetch_catalog_stats(db, user_id)
        context_parts.append(f"[시청 통계]\n{stats}")
    except Exception as e:
        logger.warning("catalog stats failed: %s", e)

    # 3. 벡터 검색 (질문 관련 영상)
    try:
        vecs = embed_texts([question])
        if vecs:
            catalog_hits = await _vector_search_catalog(db, user_id, vecs[0])
            analysis_hits = await _vector_search_analysis(db, user_id, vecs[0])
            if catalog_hits:
                context_parts.append("[관련 시청 영상]\n" + "\n".join(catalog_hits))
            if analysis_hits:
                context_parts.append("[관련 영상 분석]\n" + "\n".join(analysis_hits))
    except Exception as e:
        logger.warning("vector search failed: %s", e)

    retrieval_context = "\n\n".join(context_parts) if context_parts else "(데이터 없음)"
    return {"retrieval_context": retrieval_context}
