"""user_analysis_source — 업로드 소스별 분석 이력."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_analysis_source import (
    AnalysisSourceStage,
    AnalysisSourceStatus,
    UserAnalysisSource,
)


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
    """소스를 큐에 등록(pending). 실제 실행은 IndexerService가 유저별 직렬 처리.

    Returns (row, action): queued | skip_completed | skip_running | skip_pending.
    """
    existing = await fetch_source(session, user_id, source_key)
    if existing is not None:
        if existing.status == AnalysisSourceStatus.COMPLETED:
            return existing, "skip_completed"
        if existing.status == AnalysisSourceStatus.RUNNING:
            return existing, "skip_running"
        if existing.status == AnalysisSourceStatus.PENDING:
            return existing, "skip_pending"
        # failed 등 → 재큐
        existing.status = AnalysisSourceStatus.PENDING
        existing.stage = AnalysisSourceStage.INDEXING
        existing.file_name = file_name
        existing.profile_history_id = None
        await session.flush()
        return existing, "queued"

    row = UserAnalysisSource(
        user_id=user_id,
        source_key=source_key,
        file_name=file_name,
        status=AnalysisSourceStatus.PENDING,
        stage=AnalysisSourceStage.INDEXING,
    )
    session.add(row)
    await session.flush()
    return row, "queued"


async def count_pending_sources(session: AsyncSession, user_id: uuid.UUID) -> int:
    """유저의 대기(pending) 인덱싱 소스 수 — profile-once 판단용."""
    result = await session.execute(
        select(func.count())
        .select_from(UserAnalysisSource)
        .where(
            UserAnalysisSource.user_id == user_id,
            UserAnalysisSource.status == AnalysisSourceStatus.PENDING,
        )
    )
    return int(result.scalar_one() or 0)


async def mark_source_running(session: AsyncSession, source_id: uuid.UUID) -> None:
    """pending → running/indexing (디스패처가 실제 실행 시작 시)."""
    row = await session.get(UserAnalysisSource, source_id)
    if row is None:
        return
    row.status = AnalysisSourceStatus.RUNNING
    row.stage = AnalysisSourceStage.INDEXING


async def fail_orphan_sources(session: AsyncSession) -> int:
    """기동 시 남은 pending/running(고아) → failed.

    인메모리 큐가 재시작으로 비었으므로, 이전 프로세스의 진행 중 소스는 되살릴 수 없다.
    화면에 '분류/분석 중'이 영구 표시되는 것을 방지(S1 안전망).
    """
    result = await session.execute(
        update(UserAnalysisSource)
        .where(
            UserAnalysisSource.status.in_(
                [AnalysisSourceStatus.PENDING, AnalysisSourceStatus.RUNNING]
            )
        )
        .values(status=AnalysisSourceStatus.FAILED)
    )
    return result.rowcount or 0


async def mark_source_stage(
    session: AsyncSession, source_id: uuid.UUID, stage: str
) -> None:
    """진행 단계 갱신 (indexing → profiling). 표시용."""
    row = await session.get(UserAnalysisSource, source_id)
    if row is None:
        return
    row.stage = stage


async def fetch_active_sources(
    session: AsyncSession, user_id: uuid.UUID
) -> list[UserAnalysisSource]:
    """진행 중(pending/running) 소스 목록 — 대기중/분류중/분석중 표시용. 최신순."""
    result = await session.execute(
        select(UserAnalysisSource)
        .where(
            UserAnalysisSource.user_id == user_id,
            UserAnalysisSource.status.in_(
                [AnalysisSourceStatus.PENDING, AnalysisSourceStatus.RUNNING]
            ),
        )
        .order_by(UserAnalysisSource.created_at.desc())
    )
    return list(result.scalars().all())


async def fetch_user_source_status_map(
    session: AsyncSession, user_id: uuid.UUID
) -> dict[str, dict[str, str]]:
    """유저의 모든 소스 {source_key: {status, stage}} 매핑 (Drive 파일 목록 표시용)."""
    result = await session.execute(
        select(
            UserAnalysisSource.source_key,
            UserAnalysisSource.status,
            UserAnalysisSource.stage,
        ).where(UserAnalysisSource.user_id == user_id)
    )
    return {
        key: {"status": status, "stage": stage} for key, status, stage in result.all()
    }


async def complete_indexed_siblings(session: AsyncSession, user_id: uuid.UUID) -> None:
    """유저의 running/indexed(분류 완료) 소스 전부 completed로 — 배치 분석 끝났을 때 일괄 완료."""
    await session.execute(
        update(UserAnalysisSource)
        .where(
            UserAnalysisSource.user_id == user_id,
            UserAnalysisSource.status == AnalysisSourceStatus.RUNNING,
            UserAnalysisSource.stage == AnalysisSourceStage.INDEXED,
        )
        .values(status=AnalysisSourceStatus.COMPLETED)
    )


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
