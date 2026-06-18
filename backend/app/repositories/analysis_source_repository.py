"""user_analysis_source — 업로드 소스별 분석 이력."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_analysis_source import AnalysisSourceStatus, UserAnalysisSource


async def fetch_source(
    session: AsyncSession, user_id: uuid.UUID, source_key: str
) -> UserAnalysisSource | None:
    return (
        await session.execute(
            select(UserAnalysisSource).where(
                UserAnalysisSource.user_id == user_id,
                UserAnalysisSource.source_key == source_key,
            )
        )
    ).scalar_one_or_none()


async def begin_source(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_key: str,
    file_name: str | None,
) -> tuple[UserAnalysisSource, str]:
    """Returns (row, action): run | skip_completed | skip_running."""
    existing = await fetch_source(session, user_id, source_key)
    if existing is not None:
        if existing.status == AnalysisSourceStatus.COMPLETED:
            return existing, "skip_completed"
        if existing.status == AnalysisSourceStatus.RUNNING:
            return existing, "skip_running"
        existing.status = AnalysisSourceStatus.RUNNING
        existing.file_name = file_name
        existing.profile_history_id = None
        await session.flush()
        return existing, "run"

    row = UserAnalysisSource(
        user_id=user_id,
        source_key=source_key,
        file_name=file_name,
        status=AnalysisSourceStatus.RUNNING,
    )
    session.add(row)
    await session.flush()
    return row, "run"


async def mark_source_completed(
    session: AsyncSession,
    source_id: uuid.UUID,
    profile_history_id: uuid.UUID | None,
) -> None:
    row = await session.get(UserAnalysisSource, source_id)
    if row is None:
        return
    row.status = AnalysisSourceStatus.COMPLETED
    row.profile_history_id = profile_history_id


async def mark_source_failed(session: AsyncSession, source_id: uuid.UUID) -> None:
    row = await session.get(UserAnalysisSource, source_id)
    if row is None:
        return
    row.status = AnalysisSourceStatus.FAILED


async def delete_sources_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        delete(UserAnalysisSource).where(UserAnalysisSource.user_id == user_id)
    )
