"""업로드 소스 키 생성 및 분석 이력 갱신."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid

from app.core.database.session import AsyncSessionLocal
from app.models.analysis_batch import AnalysisBatchStatus
from app.models.user_analysis_source import AnalysisSourceStage
from app.repositories.analysis_source_repository import (
    batch_ready_to_profile,
    complete_batch_sources,
    fail_batch_sources,
    fetch_batch_source_ids,
    fetch_stuck_open_batches,
    mark_batch_status,
    mark_source_completed,
    mark_source_failed,
    mark_source_running,
    mark_source_stage,
    seal_batch,
    set_batch_sources_stage,
    try_start_batch_profiling,
)

logger = logging.getLogger(__name__)

# 자동-seal 안전망: seal이 이 시간(분) 넘게 안 오면 서버가 배치를 대신 닫는다.
BATCH_SEAL_TIMEOUT_MIN = 3
# 안전망 점검 주기(초).
BATCH_RECONCILE_INTERVAL_SEC = 60


def drive_source_key(file_id: str) -> str:
    return f"drive:{file_id}"


def upload_source_key(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"upload:{digest}"


async def delete_analysis_job_async(
    user_id: str,
    *,
    batch_id: str | None = None,
    source_id: str | None = None,
) -> bool:
    """진행중 분석(배치 또는 단일 소스) 삭제(취소). 소유자 스코프. 삭제 성공 여부."""
    from app.repositories.analysis_source_repository import (
        delete_batch_with_sources,
        delete_source_by_id,
    )

    uid = uuid.UUID(user_id)
    async with AsyncSessionLocal() as session:
        if batch_id:
            n = await delete_batch_with_sources(session, uid, uuid.UUID(batch_id))
        elif source_id:
            n = await delete_source_by_id(session, uid, uuid.UUID(source_id))
        else:
            n = 0
        await session.commit()
    return n > 0


async def complete_source_async(
    source_id: uuid.UUID | str | None,
    profile_history_id: uuid.UUID | str | None,
) -> None:
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    pid = uuid.UUID(str(profile_history_id)) if profile_history_id else None
    async with AsyncSessionLocal() as session:
        await mark_source_completed(session, sid, pid)
        await session.commit()


async def fail_source_async(source_id: uuid.UUID | str | None) -> None:
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    async with AsyncSessionLocal() as session:
        await mark_source_failed(session, sid)
        await session.commit()


async def complete_analysis_batch_async(
    source_ids: list[uuid.UUID | str] | None,
    profile_history_id: uuid.UUID | str | None,
    batch_id: uuid.UUID | str | None,
) -> None:
    """배치 분석 성공 완료 — 배치 전 소스 completed(+스냅샷 연결) + 배치 done."""
    ids = [uuid.UUID(str(s)) for s in (source_ids or [])]
    pid = uuid.UUID(str(profile_history_id)) if profile_history_id else None
    async with AsyncSessionLocal() as session:
        await complete_batch_sources(session, ids, pid)
        if batch_id is not None:
            await mark_batch_status(
                session, uuid.UUID(str(batch_id)), AnalysisBatchStatus.DONE
            )
        await session.commit()


async def fail_analysis_batch_async(
    source_ids: list[uuid.UUID | str] | None,
    batch_id: uuid.UUID | str | None,
) -> None:
    """배치 분석 실패 — 배치 전 소스 failed + 배치 done(종료)."""
    ids = [uuid.UUID(str(s)) for s in (source_ids or [])]
    async with AsyncSessionLocal() as session:
        await fail_batch_sources(session, ids)
        if batch_id is not None:
            await mark_batch_status(
                session, uuid.UUID(str(batch_id)), AnalysisBatchStatus.DONE
            )
        await session.commit()


async def seal_batch_async(
    user_id: uuid.UUID | str, batch_id: uuid.UUID | str, email: str = ""
) -> None:
    """배치를 닫고(open→sealed) 트리거 조건이 되면 프로파일러를 돌린다."""
    async with AsyncSessionLocal() as session:
        await seal_batch(session, uuid.UUID(str(batch_id)))
        await session.commit()
    await maybe_trigger_batch_async(user_id, batch_id, email)


async def maybe_trigger_batch_async(
    user_id: uuid.UUID | str, batch_id: uuid.UUID | str | None, email: str = ""
) -> None:
    """seal됨 + 배치 모든 소스 인덱싱 완료면 프로파일러 1회 트리거.

    트리거 2지점(파일 인덱싱 완료·seal)에서 호출되며, sealed→profiling 원자 전환에
    성공한 호출만 실제로 발사한다(중복 방지).
    """
    if batch_id is None:
        return
    bid = uuid.UUID(str(batch_id))
    async with AsyncSessionLocal() as session:
        if not await batch_ready_to_profile(session, bid):
            return
        if not await try_start_batch_profiling(session, bid):
            await session.commit()  # 다른 호출이 이미 발사함
            return
        source_ids = await fetch_batch_source_ids(session, bid)
        await set_batch_sources_stage(session, bid, AnalysisSourceStage.PROFILING)
        await session.commit()

    from app.services.profiler.service import profiler_service

    profiler_service.enqueue_for_user(
        str(user_id),
        email,
        analysis_source_ids=[str(s) for s in source_ids],
        batch_id=str(bid),
    )
    logger.info("[batch] 프로파일러 트리거 batch=%s sources=%d", bid, len(source_ids))


async def reconcile_stuck_batches() -> int:
    """seal 미도착으로 방치된 배치를 감지해 자동 seal + 트리거 (안전망).

    정상은 업로드 직후 수 초 내 seal이 온다. 오래(BATCH_SEAL_TIMEOUT_MIN) 안 오면
    프론트 seal 누락으로 보고 WARNING 로그를 남긴 뒤 서버가 대신 닫는다.
    """
    async with AsyncSessionLocal() as session:
        stuck = await fetch_stuck_open_batches(session, BATCH_SEAL_TIMEOUT_MIN)
    for batch_id, user_id, email in stuck:
        logger.warning(
            "[batch] seal 미도착 자동 마감 batch=%s user=%s (%d분+ 경과) "
            "— 프론트 seal 누락 의심",
            batch_id,
            user_id,
            BATCH_SEAL_TIMEOUT_MIN,
        )
        try:
            await seal_batch_async(user_id, batch_id, email or "")
        except Exception:
            logger.exception("[batch] 자동 seal 실패 batch=%s", batch_id)
    return len(stuck)


async def batch_reconcile_loop() -> None:
    """자동-seal 안전망 주기 실행 루프 (lifespan에서 기동)."""
    while True:
        try:
            await reconcile_stuck_batches()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[batch] reconcile tick 실패")
        await asyncio.sleep(BATCH_RECONCILE_INTERVAL_SEC)


async def mark_source_running_async(source_id: uuid.UUID | str | None) -> None:
    """pending → running/indexing (디스패처가 실제 실행 시작 시)."""
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    async with AsyncSessionLocal() as session:
        await mark_source_running(session, sid)
        await session.commit()


async def set_source_stage_async(source_id: uuid.UUID | str | None, stage: str) -> None:
    """진행 단계(indexing→profiling) 갱신. 표시용."""
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    async with AsyncSessionLocal() as session:
        await mark_source_stage(session, sid, stage)
        await session.commit()
