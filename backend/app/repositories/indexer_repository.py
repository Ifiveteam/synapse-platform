"""Async DB operations for the indexer (user_watch_catalog)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_watch_catalog import UserWatchCatalog
from app.models.video_analysis import VideoAnalysis


def parse_watched_at(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def catalog_row_values(user_id: uuid.UUID, item: dict) -> dict:
    """Pipeline dict → user_watch_catalog insert/update values."""
    watched_at = parse_watched_at(item.get("watched_at"))
    tags = item.get("tags")
    if tags is None and item.get("keywords"):
        tags = item.get("keywords")

    category_id = item.get("youtube_category_id") or item.get("category_id")
    if category_id is not None:
        category_id = str(category_id)[:10]

    duration = item.get("duration_sec")
    if duration is None:
        duration = item.get("duration")

    return {
        "user_id": user_id,
        "platform": item.get("platform") or "youtube",
        "channel": item.get("channel") or "unknown",
        "channel_url": item.get("channel_url"),
        "title": item.get("title"),
        "url": item.get("url"),
        "watched_at": watched_at,
        "youtube_category_id": category_id,
        "duration_sec": duration,
        "is_shorts": item.get("is_shorts"),
        "description": item.get("description"),
        "tags": tags,
        "thumbnail_url": item.get("thumbnail_url"),
        "embedding_text": item.get("embedding_text"),
        "embedding": item.get("embedding"),
    }


_UPSERT_COLUMNS = (
    "platform",
    "channel",
    "channel_url",
    "title",
    "watched_at",
    "youtube_category_id",
    "duration_sec",
    "is_shorts",
    "description",
    "tags",
    "thumbnail_url",
    "embedding_text",
    "embedding",
)


async def upsert_catalog_records(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[dict],
) -> int:
    """Bulk upsert into user_watch_catalog. UNIQUE (user_id, url)."""
    count = 0
    for item in items:
        if not item.get("url"):
            continue
        values = catalog_row_values(user_id, item)
        insert_stmt = pg_insert(UserWatchCatalog).values(**values)
        stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_uwc_user_url",
            set_={col: getattr(insert_stmt.excluded, col) for col in _UPSERT_COLUMNS},
        )
        await session.execute(stmt)
        count += 1
    return count


async def delete_user_catalog(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    include_analysis: bool = True,
) -> None:
    """Reindex: video_analysis then catalog (FK order)."""
    if include_analysis:
        await session.execute(
            delete(VideoAnalysis).where(VideoAnalysis.user_id == user_id)
        )
    await session.execute(
        delete(UserWatchCatalog).where(UserWatchCatalog.user_id == user_id)
    )


async def count_catalog(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(UserWatchCatalog)
        .where(UserWatchCatalog.user_id == user_id)
    )
    return int(result.scalar() or 0)


async def get_all_catalog(
    session: AsyncSession, user_id: uuid.UUID | None = None
) -> list[UserWatchCatalog]:
    query = select(UserWatchCatalog).order_by(UserWatchCatalog.watched_at.desc())
    if user_id is not None:
        query = query.where(UserWatchCatalog.user_id == user_id)
    result = await session.execute(query)
    return list(result.scalars().all())


def _listable_channel_conditions():
    """Placeholder·빈 채널명은 상위 채널 집계에서 제외."""
    trimmed = func.trim(UserWatchCatalog.channel)
    return (
        UserWatchCatalog.channel.isnot(None),
        trimmed != "",
        func.lower(trimmed) != "unknown",
    )


async def fetch_top_categories(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 5,
) -> list[dict[str, int | str]]:
    """user_watch_catalog GROUP BY youtube_category_id — 상위 N개."""
    rows = await session.execute(
        select(UserWatchCatalog.youtube_category_id, func.count())
        .where(UserWatchCatalog.user_id == user_id)
        .group_by(UserWatchCatalog.youtube_category_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {"category_id": str(row[0] or "unknown"), "count": int(row[1])}
        for row in rows.all()
    ]


async def fetch_top_channels(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 5,
) -> list[dict[str, int | str]]:
    """user_watch_catalog GROUP BY channel — 상위 N개."""
    rows = await session.execute(
        select(UserWatchCatalog.channel, func.count())
        .where(UserWatchCatalog.user_id == user_id, *_listable_channel_conditions())
        .group_by(UserWatchCatalog.channel)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {"channel": str(row[0] or "unknown"), "count": int(row[1])}
        for row in rows.all()
    ]


async def fetch_graph_summary(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    category_limit: int = 8,
    channel_limit: int = 10,
) -> dict:
    """그래프 UI용 catalog 집계 — 전체 영상 목록 없이 상위 카테고리·채널만."""
    total = await count_catalog(session, user_id)
    categories = await fetch_top_categories(session, user_id, limit=category_limit)
    top_channels = await fetch_top_channels(session, user_id, limit=channel_limit)

    channels: list[dict[str, int | str]] = []
    for item in top_channels:
        channel_name = str(item["channel"])
        row = await session.execute(
            select(UserWatchCatalog.youtube_category_id, func.count())
            .where(
                UserWatchCatalog.user_id == user_id,
                UserWatchCatalog.channel == channel_name,
            )
            .group_by(UserWatchCatalog.youtube_category_id)
            .order_by(func.count().desc())
            .limit(1)
        )
        primary = row.first()
        channels.append(
            {
                "channel": channel_name,
                "count": int(item["count"]),
                "category_id": str(primary[0] or "unknown") if primary else "unknown",
            }
        )

    return {"total": total, "categories": categories, "channels": channels}


async def fetch_catalog_embedding_rows(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    """임베딩 그래프용 catalog 행 (embedding 있는 것만)."""
    rows = await session.execute(
        select(
            UserWatchCatalog.id,
            UserWatchCatalog.title,
            UserWatchCatalog.channel,
            UserWatchCatalog.youtube_category_id,
            UserWatchCatalog.is_shorts,
            UserWatchCatalog.embedding,
        )
        .where(
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.embedding.isnot(None),
        )
        .order_by(UserWatchCatalog.watched_at.desc())
    )
    result: list[dict] = []
    for row in rows.all():
        embedding = row.embedding
        if embedding is None:
            continue
        vector = list(embedding) if not isinstance(embedding, list) else embedding
        if not vector:
            continue
        result.append(
            {
                "id": row.id,
                "title": row.title,
                "channel": row.channel,
                "youtube_category_id": row.youtube_category_id,
                "is_shorts": row.is_shorts,
                "embedding": vector,
            }
        )
    return result


async def compute_catalog_stats(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """UI 집계 — catalog 쿼리만 사용."""
    total = await count_catalog(session, user_id)

    if total == 0:
        return {
            "total": 0,
            "shorts_count": 0,
            "long_count": 0,
            "category_stats": {},
            "channel_top5": [],
        }

    shorts_q = (
        select(func.count())
        .select_from(UserWatchCatalog)
        .where(
            UserWatchCatalog.user_id == user_id, UserWatchCatalog.is_shorts.is_(True)
        )
    )
    shorts_count = (await session.execute(shorts_q)).scalar() or 0

    cat_rows = await session.execute(
        select(UserWatchCatalog.youtube_category_id, func.count())
        .where(UserWatchCatalog.user_id == user_id)
        .group_by(UserWatchCatalog.youtube_category_id)
        .order_by(func.count().desc())
    )
    category_stats = {(row[0] or "unknown"): row[1] for row in cat_rows.all()}

    ch_rows = await session.execute(
        select(UserWatchCatalog.channel, func.count())
        .where(UserWatchCatalog.user_id == user_id, *_listable_channel_conditions())
        .group_by(UserWatchCatalog.channel)
        .order_by(func.count().desc())
        .limit(5)
    )
    channel_top5 = [{"name": row[0], "count": row[1]} for row in ch_rows.all()]

    return {
        "total": total,
        "shorts_count": shorts_count,
        "long_count": total - shorts_count,
        "category_stats": category_stats,
        "channel_top5": channel_top5,
    }
