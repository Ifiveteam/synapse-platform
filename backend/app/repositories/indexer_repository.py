"""Async DB operations for the indexer agent."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.indexer.prompt import CATEGORY_LIST, normalize_category
from app.models.user_feature_snapshot import UserFeatureSnapshot
from app.models.user_video_watch import UserVideoWatch


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


def _watch_values(user_id: uuid.UUID, item: dict) -> dict:
    watched_at = parse_watched_at(item.get("watched_at"))
    keywords = item.get("keywords") or []
    return {
        "user_id": user_id,
        "platform": "youtube",
        "channel": item.get("channel") or "unknown",
        "channel_url": item.get("channel_url"),
        "title": item.get("title"),
        "url": item.get("url"),
        "watched_at": watched_at,
        "duration": item.get("duration", 0),
        "is_shorts": item.get("is_shorts", False),
        "description": item.get("description"),
        "category": item.get("category"),
        "tags": keywords,
        "thumbnail_url": item.get("thumbnail_url"),
        "transcript": item.get("transcript"),
    }


def _build_feature_snapshot(
    user_id: uuid.UUID,
    items: list[dict],
    analysis_start: datetime,
    analysis_end: datetime,
) -> dict | None:
    if not items:
        return None

    total = len(items)

    categories = [normalize_category(i.get("category")) for i in items]
    cat_counter = Counter(categories)
    category_ratio = {
        cat: round(cat_counter.get(cat, 0) / total, 4) for cat in CATEGORY_LIST
    }
    category_top5 = [{"name": k, "count": v} for k, v in cat_counter.most_common(5)]

    shorts = sum(1 for i in items if i.get("is_shorts"))
    video_type_ratio = {
        "short": round(shorts / total, 4),
        "long": round((total - shorts) / total, 4),
        "total": total,
    }

    channel_counter = Counter(i.get("channel") or "unknown" for i in items)
    channel_top5 = [{"name": k, "count": v} for k, v in channel_counter.most_common(5)]

    cat_channels: dict[str, set[str]] = defaultdict(set)
    for item in items:
        cat = normalize_category(item.get("category"))
        cat_channels[cat].add(item.get("channel") or "unknown")
    category_channel_diversity = {k: len(v) for k, v in cat_channels.items()}

    return {
        "user_id": user_id,
        "analysis_start": analysis_start,
        "analysis_end": analysis_end,
        "category_ratio": category_ratio,
        "video_type_ratio": video_type_ratio,
        "channel_top5": channel_top5,
        "category_top5": category_top5,
        "category_channel_diversity": category_channel_diversity,
    }


async def upsert_feature_snapshot(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[dict],
    analysis_start: datetime,
    analysis_end: datetime,
) -> None:
    payload = _build_feature_snapshot(user_id, items, analysis_start, analysis_end)
    if payload is None:
        return

    stmt = (
        pg_insert(UserFeatureSnapshot)
        .values(**payload)
        .on_conflict_do_update(
            constraint="uq_ufs_user_period",
            set_={
                "category_ratio": payload["category_ratio"],
                "video_type_ratio": payload["video_type_ratio"],
                "channel_top5": payload["channel_top5"],
                "category_top5": payload["category_top5"],
                "category_channel_diversity": payload["category_channel_diversity"],
            },
        )
    )
    await session.execute(stmt)


async def save_watch_records(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[dict],
) -> None:
    for item in items:
        values = _watch_values(user_id, item)
        watch_stmt = (
            pg_insert(UserVideoWatch)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_uvw_user_url",
                set_={
                    "channel": values["channel"],
                    "channel_url": values["channel_url"],
                    "title": values["title"],
                    "watched_at": values["watched_at"],
                    "duration": values["duration"],
                    "is_shorts": values["is_shorts"],
                    "description": values["description"],
                    "category": values["category"],
                    "tags": values["tags"],
                    "thumbnail_url": values["thumbnail_url"],
                    "transcript": values["transcript"],
                },
            )
        )
        await session.execute(watch_stmt)


async def save_vectors(
    items: list[dict],
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> None:
    """레거시 호환 — watch + snapshot 한 번에 저장."""
    if user_id is None:
        raise ValueError("user_id is required to save watch records")

    await save_watch_records(session, user_id, items)
    if items:
        watched_dates = [parse_watched_at(i.get("watched_at")) for i in items]
        await upsert_feature_snapshot(
            session,
            user_id,
            items,
            min(watched_dates),
            max(watched_dates),
        )
    await session.commit()


async def update_all_weights(
    session: AsyncSession, user_id: uuid.UUID | None = None
) -> int:
    """Legacy hook — weight column removed in user_video_watch schema."""
    _ = session, user_id
    return 0


async def is_duplicate(
    url: str,
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> bool:
    query = select(UserVideoWatch.id).where(UserVideoWatch.url == url).limit(1)
    if user_id is not None:
        query = query.where(UserVideoWatch.user_id == user_id)
    result = await session.execute(query)
    return result.scalar() is not None


async def get_all_videos(
    session: AsyncSession, user_id: uuid.UUID | None = None
) -> list[UserVideoWatch]:
    query = select(UserVideoWatch).order_by(UserVideoWatch.watched_at.desc())
    if user_id is not None:
        query = query.where(UserVideoWatch.user_id == user_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_user_vector(
    session: AsyncSession, user_id: uuid.UUID | None = None
) -> list[float]:
    """임베딩 미사용 — 프로파일러 단계에서 video_analysis 생성 예정."""
    _ = session, user_id
    return []
