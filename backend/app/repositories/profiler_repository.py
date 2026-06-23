"""Profiler DB — catalog reads, video_analysis, user_profile_history."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile_history import UserProfileHistory
from app.models.user_watch_catalog import UserWatchCatalog
from app.models.video_analysis import VideoAnalysis
from app.schemas.profiler import ProfileInsightOutput, ProfileScoresOutput


async def fetch_latest_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> UserProfileHistory | None:
    return (
        await session.execute(
            select(UserProfileHistory)
            .where(UserProfileHistory.user_id == user_id)
            .order_by(desc(UserProfileHistory.snapshot_date))
            .limit(1)
        )
    ).scalar_one_or_none()


async def fetch_profile_history_list(
    session: AsyncSession, user_id: uuid.UUID
) -> list[UserProfileHistory]:
    result = await session.execute(
        select(UserProfileHistory)
        .where(UserProfileHistory.user_id == user_id)
        .order_by(desc(UserProfileHistory.snapshot_date))
    )
    return list(result.scalars().all())


async def fetch_profile_snapshot(
    session: AsyncSession, user_id: uuid.UUID, snapshot_id: uuid.UUID
) -> UserProfileHistory | None:
    return (
        await session.execute(
            select(UserProfileHistory).where(
                UserProfileHistory.user_id == user_id,
                UserProfileHistory.id == snapshot_id,
            )
        )
    ).scalar_one_or_none()


async def fetch_catalog_rows(
    session: AsyncSession, user_id: uuid.UUID
) -> list[UserWatchCatalog]:
    result = await session.execute(
        select(UserWatchCatalog)
        .where(UserWatchCatalog.user_id == user_id)
        .order_by(desc(UserWatchCatalog.watched_at))
    )
    return list(result.scalars().all())


async def fetch_unanalyzed_catalog(
    session: AsyncSession, user_id: uuid.UUID, limit: int | None = None
) -> list[UserWatchCatalog]:
    """요약이 없는 catalog 행 (video_summary 대상)."""
    analyzed_subq = select(VideoAnalysis.id).where(
        VideoAnalysis.catalog_id == UserWatchCatalog.id,
        VideoAnalysis.summary_kr.isnot(None),
    )
    query = (
        select(UserWatchCatalog)
        .where(UserWatchCatalog.user_id == user_id)
        .where(~analyzed_subq.exists())
        .order_by(desc(UserWatchCatalog.watched_at))
    )
    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def upsert_video_analysis(
    session: AsyncSession, analyzed: Sequence[Mapping[str, Any]]
) -> int:
    """영상 분석 결과를 video_analysis에 upsert."""
    saved = 0
    for row in analyzed:
        embedding = row.get("embedding")
        if embedding is None:
            continue

        values = {
            "catalog_id": row["catalog_id"],
            "user_id": row["user_id"],
            "summary_kr": row["summary_kr"],
            "tones": row["tones"],
            "intents": row["intents"],
            "value_signals": row["value_signals"],
            "transcript": row.get("transcript"),
            "embedding_text": row["embedding_text"],
            "embedding": embedding,
        }
        stmt = (
            pg_insert(VideoAnalysis)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["catalog_id"],
                set_={
                    "summary_kr": values["summary_kr"],
                    "tones": values["tones"],
                    "intents": values["intents"],
                    "value_signals": values["value_signals"],
                    "transcript": values["transcript"],
                    "embedding_text": values["embedding_text"],
                    "embedding": values["embedding"],
                    "updated_at": func.now(),
                },
            )
        )
        await session.execute(stmt)
        saved += 1

    return saved


async def fetch_analysis_for_catalog_ids(
    session: AsyncSession, catalog_ids: list[uuid.UUID]
) -> list[VideoAnalysis]:
    if not catalog_ids:
        return []
    result = await session.execute(
        select(VideoAnalysis).where(VideoAnalysis.catalog_id.in_(catalog_ids))
    )
    return list(result.scalars().all())


async def fetch_video_analyses_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 50,
) -> list[VideoAnalysis]:
    """유저 video_analysis 전체 (build_profile 샘플 우선순위용)."""
    result = await session.execute(
        select(VideoAnalysis)
        .where(VideoAnalysis.user_id == user_id)
        .order_by(desc(VideoAnalysis.updated_at))
        .limit(limit)
    )
    return list(result.scalars().all())


def profile_snapshot_from_outputs(
    user_id: uuid.UUID,
    snapshot_date: datetime,
    scores: ProfileScoresOutput,
    insight: ProfileInsightOutput,
    supporting_evidence: dict[str, Any],
) -> UserProfileHistory:
    return UserProfileHistory(
        user_id=user_id,
        snapshot_date=snapshot_date,
        **scores.model_dump(),
        summary_text=insight.summary_text,
        persona_label=insight.persona_label,
        behavior_reasoning=insight.behavior_reasoning,
        dominant_traits=insight.dominant_traits,
        supporting_evidence=supporting_evidence,
        tone_of_user=insight.tone_of_user,
    )


async def insert_profile_snapshot(
    session: AsyncSession,
    user_id: uuid.UUID,
    scores: ProfileScoresOutput,
    insight: ProfileInsightOutput,
    supporting_evidence: dict[str, Any],
    *,
    snapshot_date: datetime | None = None,
) -> uuid.UUID:
    when = snapshot_date or datetime.now(UTC)
    row = profile_snapshot_from_outputs(
        user_id, when, scores, insight, supporting_evidence
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row.id
