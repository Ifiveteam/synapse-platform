"""영상요약 서브에이전트의 async DB 연산."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.profiler.video_summary.state import AnalyzedVideo
from app.models.user_video_watch import UserVideoWatch
from app.models.video_analysis import VideoAnalysis


async def fetch_unanalyzed_watches(
    session: AsyncSession, user_id: uuid.UUID, limit: int | None = None
) -> list[UserVideoWatch]:
    """아직 의미분석되지 않은 user_video_watch만 조회 (재실행 멱등성).

    '미분석' = video_analysis 행이 없거나, 있어도 summary_kr이 NULL(옛 인덱서가
    embedding만 채운 행). upsert가 on_conflict로 그 행을 UPDATE한다.
    """
    analyzed_subq = select(VideoAnalysis.id).where(
        VideoAnalysis.user_video_watch_id == UserVideoWatch.id,
        VideoAnalysis.summary_kr.isnot(None),
    )
    query = (
        select(UserVideoWatch)
        .where(UserVideoWatch.user_id == user_id)
        .where(~analyzed_subq.exists())
        .order_by(UserVideoWatch.watched_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def upsert_video_analysis(
    session: AsyncSession, analyzed: list[AnalyzedVideo]
) -> int:
    """분석 결과를 video_analysis에 upsert. embedding 없는 항목은 건너뜀(NOT NULL)."""
    saved = 0
    for a in analyzed:
        embedding = a.get("embedding")
        if embedding is None:
            continue

        values = {
            "user_video_watch_id": a["watch_id"],
            "summary_kr": a["summary_kr"],
            "tones": a["tones"],
            "intents": a["intents"],
            "value_signals": a["value_signals"],
            "embedding_text": a["embedding_text"],
            "embedding": embedding,
        }
        stmt = (
            pg_insert(VideoAnalysis)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["user_video_watch_id"],
                set_={
                    "summary_kr": values["summary_kr"],
                    "tones": values["tones"],
                    "intents": values["intents"],
                    "value_signals": values["value_signals"],
                    "embedding_text": values["embedding_text"],
                    "embedding": values["embedding"],
                },
            )
        )
        await session.execute(stmt)
        saved += 1

    await session.commit()
    return saved
