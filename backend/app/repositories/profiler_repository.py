"""Profiler DB — catalog reads, video_analysis, user_profile_history."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_source_catalog import AnalysisSourceCatalog
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


async def fetch_recent_catalog_rows(
    session: AsyncSession, user_id: uuid.UUID, window_days: int
) -> list[UserWatchCatalog]:
    """누적 catalog 중 최근 시청 기준 window_days 이내 행만 (프로파일러 채점용 롤링 윈도우).

    기준점은 '오늘'이 아니라 그 유저의 가장 최근 시청 시각(max watched_at)이다 —
    한동안 import가 없어도 마지막 활동 기준 최근 N일을 안정적으로 잡기 위함.
    """
    anchor = (
        await session.execute(
            select(func.max(UserWatchCatalog.watched_at)).where(
                UserWatchCatalog.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if anchor is None:
        return []
    start = anchor - timedelta(days=window_days)
    result = await session.execute(
        select(UserWatchCatalog)
        .where(
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.watched_at >= start,
        )
        .order_by(desc(UserWatchCatalog.watched_at))
    )
    return list(result.scalars().all())


async def fetch_catalog_rows_by_sources(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_ids: list[uuid.UUID | str],
    window_days: int,
) -> list[UserWatchCatalog]:
    """배치 소스들에 소속된 catalog 행 중 최근 window_days (합집합 후 2달 재컷).

    앵커(기준점)는 그 배치 집합 내 가장 최근 시청 시각. 소속은 analysis_source_catalog
    조인으로 판정(catalog_id DISTINCT)한다. source_ids 없으면 빈 목록.
    """
    if not source_ids:
        return []
    sids = [uuid.UUID(str(s)) for s in source_ids]
    catalog_ids_subq = (
        select(AnalysisSourceCatalog.catalog_id)
        .where(AnalysisSourceCatalog.analysis_source_id.in_(sids))
        .distinct()
    )
    anchor = (
        await session.execute(
            select(func.max(UserWatchCatalog.watched_at)).where(
                UserWatchCatalog.user_id == user_id,
                UserWatchCatalog.id.in_(catalog_ids_subq),
            )
        )
    ).scalar_one_or_none()
    if anchor is None:
        return []
    start = anchor - timedelta(days=window_days)
    result = await session.execute(
        select(UserWatchCatalog)
        .where(
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.id.in_(catalog_ids_subq),
            UserWatchCatalog.watched_at >= start,
        )
        .order_by(desc(UserWatchCatalog.watched_at))
    )
    return list(result.scalars().all())


async def fetch_video_analyses_by_catalog_ids(
    session: AsyncSession,
    catalog_ids: list[uuid.UUID],
    *,
    limit: int = 50,
) -> list[VideoAnalysis]:
    """주어진 catalog 행들의 video_analysis (배치 스코프 샘플용)."""
    if not catalog_ids:
        return []
    result = await session.execute(
        select(VideoAnalysis)
        .where(VideoAnalysis.catalog_id.in_(catalog_ids))
        .order_by(desc(VideoAnalysis.updated_at))
        .limit(limit)
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
                    "embedding_text": values["embedding_text"],
                    "embedding": values["embedding"],
                    "updated_at": func.now(),
                },
            )
        )
        await session.execute(stmt)
        saved += 1

    return saved


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
    batch_id: uuid.UUID | None = None,
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
        batch_id=batch_id,
    )


async def insert_profile_snapshot(
    session: AsyncSession,
    user_id: uuid.UUID,
    scores: ProfileScoresOutput,
    insight: ProfileInsightOutput,
    supporting_evidence: dict[str, Any],
    *,
    snapshot_date: datetime | None = None,
    batch_id: uuid.UUID | str | None = None,
) -> uuid.UUID:
    when = snapshot_date or datetime.now(UTC)
    bid = uuid.UUID(str(batch_id)) if batch_id else None
    row = profile_snapshot_from_outputs(
        user_id, when, scores, insight, supporting_evidence, bid
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row.id
