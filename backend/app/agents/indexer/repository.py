"""Async DB operations for the indexer agent."""

from __future__ import annotations

from datetime import datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video_vector import VideoVector


def _parse_watched_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def save_vectors(items: list[dict], session: AsyncSession) -> None:
    for item in items:
        stmt = (
            pg_insert(VideoVector)
            .values(
                title=item.get("title", ""),
                channel=item.get("channel", ""),
                channel_url=item.get("channel_url", ""),
                url=item.get("url", ""),
                watched_at=_parse_watched_at(item.get("watched_at")),
                category=item.get("category", ""),
                keywords=item.get("keywords", []),
                duration=item.get("duration", 0),
                is_shorts=item.get("is_shorts", False),
                embedding=item.get("embedding"),
            )
            .on_conflict_do_nothing(index_elements=["url"])
        )
        await session.execute(stmt)
    await session.commit()


async def is_duplicate(url: str, session: AsyncSession) -> bool:
    result = await session.execute(
        select(VideoVector.id).where(VideoVector.url == url).limit(1)
    )
    return result.scalar() is not None


async def get_all_videos(session: AsyncSession) -> list[VideoVector]:
    result = await session.execute(
        select(VideoVector).order_by(VideoVector.id.desc())
    )
    return list(result.scalars().all())


async def create_user_vector(session: AsyncSession) -> list[float]:
    result = await session.execute(
        select(VideoVector.embedding).where(VideoVector.embedding.isnot(None))
    )
    rows = result.scalars().all()
    if not rows:
        return []
    embeddings = [list(row) for row in rows]
    return np.mean(embeddings, axis=0).tolist()
