"""user_analysis_source — 업로드 소스별 분석 이력."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_batch import AnalysisBatch, AnalysisBatchStatus
from app.models.user import User
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


async def ensure_batch(
    session: AsyncSession,
    user_id: uuid.UUID,
    batch_id: uuid.UUID | str | None,
) -> uuid.UUID:
    """배치 행을 보장하고 batch_id를 돌려준다.

    - batch_id 있음(클릭 배치): 없으면 open으로 생성, 있으면 유지(on conflict do nothing)
    - batch_id 없음(단일/자동): 서버가 새 배치를 sealed로 생성 (더 올 파일 없음)
    """
    if batch_id is None:
        bid = uuid.uuid4()
        status = AnalysisBatchStatus.SEALED
    else:
        bid = uuid.UUID(str(batch_id))
        status = AnalysisBatchStatus.OPEN
    stmt = (
        pg_insert(AnalysisBatch)
        .values(id=bid, user_id=user_id, status=status)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)
    return bid


async def begin_source(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_key: str,
    file_name: str | None,
    batch_id: uuid.UUID | str | None = None,
) -> tuple[UserAnalysisSource, str]:
    """소스를 큐에 등록(pending). 실제 실행은 IndexerService가 유저별 직렬 처리.

    Returns (row, action): queued | skip_completed | skip_running | skip_pending.
    queued일 때만 배치를 보장·연결한다(skip은 기존 배치 소속 유지).
    """
    existing = await fetch_source(session, user_id, source_key)
    if existing is not None:
        if existing.status == AnalysisSourceStatus.COMPLETED:
            # 스냅샷이 삭제돼 고아가 된 완료 소스는 재분석 허용(재큐잉)
            if existing.profile_history_id is None:
                bid = await ensure_batch(session, user_id, batch_id)
                existing.status = AnalysisSourceStatus.PENDING
                existing.stage = AnalysisSourceStage.INDEXING
                existing.file_name = file_name
                existing.batch_id = bid
                await session.flush()
                return existing, "queued"
            return existing, "skip_completed"
        if existing.status == AnalysisSourceStatus.RUNNING:
            return existing, "skip_running"
        if existing.status == AnalysisSourceStatus.PENDING:
            return existing, "skip_pending"
        # failed 등 → 재큐 (이번 요청의 새 배치로 재소속)
        bid = await ensure_batch(session, user_id, batch_id)
        existing.status = AnalysisSourceStatus.PENDING
        existing.stage = AnalysisSourceStage.INDEXING
        existing.file_name = file_name
        existing.profile_history_id = None
        existing.batch_id = bid
        await session.flush()
        return existing, "queued"

    bid = await ensure_batch(session, user_id, batch_id)
    row = UserAnalysisSource(
        user_id=user_id,
        source_key=source_key,
        file_name=file_name,
        status=AnalysisSourceStatus.PENDING,
        stage=AnalysisSourceStage.INDEXING,
        batch_id=bid,
    )
    session.add(row)
    await session.flush()
    return row, "queued"


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


async def delete_source_by_id(
    session: AsyncSession, user_id: uuid.UUID, source_id: uuid.UUID
) -> int:
    """단일 진행중 소스 삭제(취소). 삭제된 행 수 반환(소유자 스코프)."""
    result = await session.execute(
        delete(UserAnalysisSource).where(
            UserAnalysisSource.user_id == user_id,
            UserAnalysisSource.id == source_id,
        )
    )
    return result.rowcount or 0


async def delete_batch_with_sources(
    session: AsyncSession, user_id: uuid.UUID, batch_id: uuid.UUID
) -> int:
    """배치와 그에 속한 소스들을 함께 삭제(취소). 삭제된 소스 수 반환."""
    result = await session.execute(
        delete(UserAnalysisSource).where(
            UserAnalysisSource.user_id == user_id,
            UserAnalysisSource.batch_id == batch_id,
        )
    )
    await session.execute(
        delete(AnalysisBatch).where(
            AnalysisBatch.id == batch_id,
            AnalysisBatch.user_id == user_id,
        )
    )
    return result.rowcount or 0


async def delete_sources_by_profile_history(
    session: AsyncSession, user_id: uuid.UUID, profile_history_id: uuid.UUID
) -> int:
    """스냅샷(분석) 삭제 시 그 분석의 소스(dedup 레코드)도 제거 → 같은 파일 재분석 허용."""
    result = await session.execute(
        delete(UserAnalysisSource).where(
            UserAnalysisSource.user_id == user_id,
            UserAnalysisSource.profile_history_id == profile_history_id,
        )
    )
    return result.rowcount or 0


# ---------------------------------------------------------------------------
# 배치 (analysis_batch) — seal·트리거·완료
# ---------------------------------------------------------------------------


async def seal_batch(session: AsyncSession, batch_id: uuid.UUID) -> None:
    """배치를 닫는다(open→sealed). 이미 sealed/profiling/done이면 no-op."""
    await session.execute(
        update(AnalysisBatch)
        .where(
            AnalysisBatch.id == batch_id,
            AnalysisBatch.status == AnalysisBatchStatus.OPEN,
        )
        .values(status=AnalysisBatchStatus.SEALED)
    )


async def fetch_batch_source_ids(
    session: AsyncSession, batch_id: uuid.UUID
) -> list[uuid.UUID]:
    """배치에 속한 소스 id 목록 (프로파일러 스코프용)."""
    result = await session.execute(
        select(UserAnalysisSource.id).where(UserAnalysisSource.batch_id == batch_id)
    )
    return [row[0] for row in result.all()]


async def batch_ready_to_profile(session: AsyncSession, batch_id: uuid.UUID) -> bool:
    """트리거 조건: sealed AND 진행 중 소스 없음 AND 인덱싱 완료 소스 ≥1."""
    status = (
        await session.execute(
            select(AnalysisBatch.status).where(AnalysisBatch.id == batch_id)
        )
    ).scalar_one_or_none()
    if status != AnalysisBatchStatus.SEALED:
        return False

    in_progress = (
        await session.execute(
            select(func.count())
            .select_from(UserAnalysisSource)
            .where(
                UserAnalysisSource.batch_id == batch_id,
                or_(
                    UserAnalysisSource.status == AnalysisSourceStatus.PENDING,
                    and_(
                        UserAnalysisSource.status == AnalysisSourceStatus.RUNNING,
                        UserAnalysisSource.stage == AnalysisSourceStage.INDEXING,
                    ),
                ),
            )
        )
    ).scalar_one()
    if int(in_progress or 0) > 0:
        return False

    indexed = (
        await session.execute(
            select(func.count())
            .select_from(UserAnalysisSource)
            .where(
                UserAnalysisSource.batch_id == batch_id,
                UserAnalysisSource.stage == AnalysisSourceStage.INDEXED,
            )
        )
    ).scalar_one()
    return int(indexed or 0) >= 1


async def try_start_batch_profiling(session: AsyncSession, batch_id: uuid.UUID) -> bool:
    """sealed→profiling 원자 전환. 성공한 호출만 True (중복 발사 방지)."""
    result = await session.execute(
        update(AnalysisBatch)
        .where(
            AnalysisBatch.id == batch_id,
            AnalysisBatch.status == AnalysisBatchStatus.SEALED,
        )
        .values(status=AnalysisBatchStatus.PROFILING)
    )
    return (result.rowcount or 0) > 0


async def mark_batch_status(
    session: AsyncSession, batch_id: uuid.UUID, status: str
) -> None:
    await session.execute(
        update(AnalysisBatch).where(AnalysisBatch.id == batch_id).values(status=status)
    )


async def complete_batch_sources(
    session: AsyncSession,
    source_ids: list[uuid.UUID],
    profile_history_id: uuid.UUID | None,
) -> None:
    """배치의 (실패하지 않은) 소스를 completed로 + 스냅샷 연결 (역방향 정합).

    인덱싱 실패한 소스는 failed 상태를 유지한다(배치 성공으로 완료 표시되지 않게).
    """
    if not source_ids:
        return
    await session.execute(
        update(UserAnalysisSource)
        .where(
            UserAnalysisSource.id.in_(source_ids),
            UserAnalysisSource.status != AnalysisSourceStatus.FAILED,
        )
        .values(
            status=AnalysisSourceStatus.COMPLETED,
            profile_history_id=profile_history_id,
        )
    )


async def fail_batch_sources(
    session: AsyncSession, source_ids: list[uuid.UUID]
) -> None:
    """분류는 됐으나 프로파일 실패 시 배치 소스들을 failed로."""
    if not source_ids:
        return
    await session.execute(
        update(UserAnalysisSource)
        .where(UserAnalysisSource.id.in_(source_ids))
        .values(status=AnalysisSourceStatus.FAILED)
    )


async def set_batch_sources_stage(
    session: AsyncSession, batch_id: uuid.UUID, stage: str
) -> None:
    """배치 소스 전체의 stage 갱신 (표시용, 예: profiling)."""
    await session.execute(
        update(UserAnalysisSource)
        .where(UserAnalysisSource.batch_id == batch_id)
        .values(stage=stage)
    )


async def fetch_stuck_open_batches(
    session: AsyncSession, older_than_minutes: int
) -> list[tuple[uuid.UUID, uuid.UUID, str | None]]:
    """seal이 안 온 채 방치된 배치 — 자동 seal 대상.

    조건: status=open AND 진행 중 소스 없음 AND 인덱싱 완료 소스 ≥1 AND
    마지막 소스 활동이 older_than_minutes 이전(=seal이 왔어야 할 시점 지남).
    Returns [(batch_id, user_id, email)].
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    in_progress = or_(
        UserAnalysisSource.status == AnalysisSourceStatus.PENDING,
        and_(
            UserAnalysisSource.status == AnalysisSourceStatus.RUNNING,
            UserAnalysisSource.stage == AnalysisSourceStage.INDEXING,
        ),
    )
    result = await session.execute(
        select(AnalysisBatch.id, AnalysisBatch.user_id, User.email)
        .join(UserAnalysisSource, UserAnalysisSource.batch_id == AnalysisBatch.id)
        .join(User, User.id == AnalysisBatch.user_id)
        .where(AnalysisBatch.status == AnalysisBatchStatus.OPEN)
        .group_by(AnalysisBatch.id, AnalysisBatch.user_id, User.email)
        .having(
            and_(
                func.count().filter(in_progress) == 0,
                func.count().filter(
                    UserAnalysisSource.stage == AnalysisSourceStage.INDEXED
                )
                >= 1,
                func.max(UserAnalysisSource.updated_at) < cutoff,
            )
        )
    )
    return [(row[0], row[1], row[2]) for row in result.all()]
