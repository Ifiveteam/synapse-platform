"""Async DB operations for the indexer agent."""

from __future__ import annotations

from datetime import datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.indexer.decay import compute_weight
from app.models.video_vector import VideoVector


def _parse_watched_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def save_vectors(
    items: list[dict], session: AsyncSession, user_id: int | None = None
) -> None:
    for item in items:
        watched_at = _parse_watched_at(item.get("watched_at"))
        stmt = (
            pg_insert(VideoVector)
            .values(
                title=item.get("title", ""),
                channel=item.get("channel", ""),
                channel_url=item.get("channel_url", ""),
                url=item.get("url", ""),
                watched_at=watched_at,
                category=item.get("category", ""),
                keywords=item.get("keywords", []),
                duration=item.get("duration", 0),
                is_shorts=item.get("is_shorts", False),
                embedding=item.get("embedding"),
                weight=compute_weight(watched_at),
                user_id=user_id,
            )
            .on_conflict_do_update(
                index_elements=["url", "user_id"],
                set_={
                    "category": item.get("category", ""),
                    "keywords": item.get("keywords", []),
                    "duration": item.get("duration", 0),
                    "is_shorts": item.get("is_shorts", False),
                    "embedding": item.get("embedding"),
                    "weight": compute_weight(watched_at),
                },
            )
        )
        await session.execute(stmt)
    await session.commit()


async def update_all_weights(session: AsyncSession, user_id: int | None = None) -> int:
    query = select(VideoVector).where(VideoVector.watched_at.isnot(None))
    if user_id is not None:
        query = query.where(VideoVector.user_id == user_id)
    result = await session.execute(query)
    videos = list(result.scalars().all())
    for v in videos:
        v.weight = compute_weight(v.watched_at)
    await session.commit()
    return len(videos)


async def is_duplicate(url: str, session: AsyncSession) -> bool:
    result = await session.execute(
        select(VideoVector.id).where(VideoVector.url == url).limit(1)
    )
    return result.scalar() is not None


async def get_all_videos(
    session: AsyncSession, user_id: int | None = None
) -> list[VideoVector]:
    query = select(VideoVector).order_by(VideoVector.watched_at.desc())
    if user_id is not None:
        query = query.where(VideoVector.user_id == user_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_user_vector(
    session: AsyncSession, user_id: int | None = None
) -> list[float]:
    query = select(VideoVector.embedding).where(VideoVector.embedding.isnot(None))
    if user_id is not None:
        query = query.where(VideoVector.user_id == user_id)
    result = await session.execute(query)
    rows = result.scalars().all()
    if not rows:
        return []
    embeddings = [list(row) for row in rows]
    return np.mean(embeddings, axis=0).tolist()
