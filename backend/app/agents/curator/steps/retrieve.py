"""retrieve 노드 — 프로필 + 시청기록 + 영상분석 벡터 검색 + 차트 데이터 emit."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.constants import (
    ANALYSIS_SEARCH_LIMIT,
    RECENT_VIDEO_LIMIT,
    TOP_CHANNEL_LIMIT,
    VIDEO_SEARCH_LIMIT,
)
from app.agents.curator.types import CuratorState
from app.agents.shared.embedding import embed_texts

logger = logging.getLogger(__name__)

_CATEGORY_NAMES: dict[str, str] = {
    "1": "영화/애니메이션",
    "2": "자동차/교통",
    "10": "음악",
    "15": "반려동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "20": "게임",
    "22": "사람/블로그",
    "23": "코미디",
    "24": "엔터테인먼트",
    "25": "뉴스/정치",
    "26": "라이프스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "비영리/사회운동",
}


def _emit_chart(writer, chart_type: str, title: str, items: list) -> None:
    writer(
        {
            "event": "chart",
            "content": json.dumps(
                {"type": chart_type, "title": title, "items": items}, ensure_ascii=False
            ),
        }
    )


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
        traits = profile.dominant_traits
        if isinstance(traits, list):
            parts.append(f"주요 특성: {', '.join(str(t) for t in traits)}")
        elif isinstance(traits, dict):
            parts.append(f"주요 특성: {traits}")
    if profile.behavior_reasoning:
        parts.append(f"행동 분석: {profile.behavior_reasoning}")
    if profile.tone_of_user:
        parts.append(f"성향 톤: {profile.tone_of_user}")
    return "\n".join(parts)


async def _fetch_catalog_stats(db: AsyncSession, user_id) -> tuple[str, list[dict]]:
    """총 통계 텍스트 + 카테고리 차트 아이템 반환."""
    from sqlalchemy import func, select

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
        select(UserWatchCatalog.youtube_category_id, func.count().label("cnt"))
        .where(UserWatchCatalog.user_id == user_id)
        .group_by(UserWatchCatalog.youtube_category_id)
        .order_by(func.count().desc())
        .limit(6)
    )
    cat_rows = cat_q.all()
    top_cats = [
        f"{_CATEGORY_NAMES.get(r[0] or '', r[0] or '미분류')}({r[1]}건)"
        for r in cat_rows
    ]

    text = (
        f"총 시청 영상: {total}개 / 쇼츠 비율: {shorts}/{total} / "
        f"주요 카테고리: {', '.join(top_cats)}"
    )
    chart_items = [
        {"label": _CATEGORY_NAMES.get(r[0] or "", r[0] or "미분류"), "count": r[1]}
        for r in cat_rows
    ]
    return text, chart_items


async def _fetch_top_channels(db: AsyncSession, user_id) -> list[Any]:
    from sqlalchemy import func, select

    from app.models.user_watch_catalog import UserWatchCatalog

    rows = (
        await db.execute(
            select(UserWatchCatalog.channel, func.count().label("cnt"))
            .where(UserWatchCatalog.user_id == user_id)
            .group_by(UserWatchCatalog.channel)
            .order_by(func.count().desc())
            .limit(TOP_CHANNEL_LIMIT)
        )
    ).fetchall()
    return rows


async def _fetch_recent_videos(db: AsyncSession, user_id) -> list[Any]:
    from sqlalchemy import desc, select

    from app.models.user_watch_catalog import UserWatchCatalog

    rows = (
        await db.execute(
            select(
                UserWatchCatalog.title,
                UserWatchCatalog.channel,
                UserWatchCatalog.watched_at,
            )
            .where(
                UserWatchCatalog.user_id == user_id,
                UserWatchCatalog.title.isnot(None),
                UserWatchCatalog.is_shorts.isnot(True),
            )
            .order_by(desc(UserWatchCatalog.watched_at))
            .limit(RECENT_VIDEO_LIMIT)
        )
    ).fetchall()
    return rows


async def _fetch_shorts(db: AsyncSession, user_id) -> list[Any]:
    from sqlalchemy import desc, select

    from app.models.user_watch_catalog import UserWatchCatalog

    rows = (
        await db.execute(
            select(
                UserWatchCatalog.title,
                UserWatchCatalog.channel,
                UserWatchCatalog.watched_at,
            )
            .where(
                UserWatchCatalog.user_id == user_id,
                UserWatchCatalog.is_shorts.is_(True),
                UserWatchCatalog.title.isnot(None),
            )
            .order_by(desc(UserWatchCatalog.watched_at))
            .limit(10)
        )
    ).fetchall()
    return rows


async def _vector_search_catalog(
    db: AsyncSession, user_id, vec: list[float]
) -> list[Any]:
    from sqlalchemy import text

    rows = (
        await db.execute(
            text("""
            SELECT title, channel, youtube_category_id,
                   1 - (embedding <=> CAST(:vec AS vector)) AS score
            FROM user_watch_catalog
            WHERE user_id = :uid AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :lim
        """),
            {"vec": str(vec), "uid": str(user_id), "lim": VIDEO_SEARCH_LIMIT},
        )
    ).fetchall()
    return rows


async def _vector_search_analysis(
    db: AsyncSession, user_id, vec: list[float]
) -> list[Any]:
    from sqlalchemy import text

    rows = (
        await db.execute(
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
        )
    ).fetchall()
    return rows


async def retrieve(state: CuratorState, db: AsyncSession) -> dict[str, Any]:
    writer = get_stream_writer()
    writer({"event": "status", "content": "🔍 데이터를 검색하고 있습니다..."})

    user_id = state["user_id"]
    question = _latest_user_message(state)
    sources = set(state.get("needed_sources") or [])
    context_parts: list[str] = []

    need_vector = "vector_catalog" in sources or "vector_analysis" in sources
    vec: list[float] | None = None
    if need_vector:
        try:
            vecs = embed_texts([question])
            vec = vecs[0] if vecs else None
        except Exception as e:
            logger.warning("embedding failed: %s", e)

    if "profile" in sources:
        try:
            from app.repositories.profiler_repository import fetch_latest_profile

            profile = await fetch_latest_profile(db, user_id)
            if profile:
                context_parts.append("[프로필]\n" + _format_profile(profile))
        except Exception as e:
            logger.warning("profile fetch failed: %s", e)

    if "stats" in sources:
        try:
            stats_text, cat_items = await _fetch_catalog_stats(db, user_id)
            context_parts.append(f"[시청 통계]\n{stats_text}")
            if cat_items:
                _emit_chart(writer, "category_bar", "카테고리별 시청 분포", cat_items)
        except Exception as e:
            logger.warning("catalog stats failed: %s", e)

    if "channels" in sources:
        try:
            rows = await _fetch_top_channels(db, user_id)
            if rows:
                context_parts.append(
                    "[자주 본 채널]\n"
                    + "\n".join(f"· {r.channel} ({r.cnt}개)" for r in rows)
                )
                _emit_chart(
                    writer,
                    "channel_rank",
                    "자주 본 채널 TOP 5",
                    [{"label": r.channel, "count": r.cnt} for r in rows],
                )
        except Exception as e:
            logger.warning("top channels failed: %s", e)

    if "recent" in sources:
        try:
            rows = await _fetch_recent_videos(db, user_id)
            if rows:
                context_parts.append(
                    "[최근 시청 영상]\n"
                    + "\n".join(f"· {r.title} ({r.channel})" for r in rows)
                )
                _emit_chart(
                    writer,
                    "video_list",
                    "최근 시청 영상",
                    [{"title": r.title, "channel": r.channel} for r in rows],
                )
        except Exception as e:
            logger.warning("recent videos failed: %s", e)

    if "shorts" in sources:
        try:
            rows = await _fetch_shorts(db, user_id)
            if rows:
                context_parts.append(
                    "[최근 시청 쇼츠]\n"
                    + "\n".join(f"· {r.title} ({r.channel})" for r in rows)
                )
                _emit_chart(
                    writer,
                    "shorts_list",
                    "최근 본 쇼츠",
                    [{"title": r.title, "channel": r.channel} for r in rows],
                )
        except Exception as e:
            logger.warning("shorts fetch failed: %s", e)

    if "vector_catalog" in sources and vec:
        try:
            rows = await _vector_search_catalog(db, user_id, vec)
            if rows:
                context_parts.append(
                    "[질문 관련 시청 영상]\n"
                    + "\n".join(f"· {r.title} ({r.channel})" for r in rows)
                )
                _emit_chart(
                    writer,
                    "video_list",
                    "관련 시청 영상",
                    [{"title": r.title, "channel": r.channel} for r in rows],
                )
        except Exception as e:
            logger.warning("vector catalog search failed: %s", e)

    if "vector_analysis" in sources and vec:
        try:
            rows = await _vector_search_analysis(db, user_id, vec)
            if rows:
                context_parts.append(
                    "[질문 관련 영상 분석]\n"
                    + "\n".join(f"· {r.summary_kr}" for r in rows)
                )
        except Exception as e:
            logger.warning("vector analysis search failed: %s", e)

    retrieval_context = "\n\n".join(context_parts) if context_parts else "(데이터 없음)"
    return {"retrieval_context": retrieval_context}
