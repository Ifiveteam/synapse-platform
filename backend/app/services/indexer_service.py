"""인덱싱 작업 유저별 직렬 실행기.

같은 유저의 Takeout은 **한 번에 하나만** 인덱싱한다(catalog·구독 테이블 동시 쓰기
충돌·교착 방지). 나머지는 DB에서 `pending`으로 대기하다 순차 실행된다.
전역 동시 실행은 세마포어로 상한을 둔다.

상태 정본은 DB(`user_analysis_source`): pending → running(indexing) → (profiler) completed.
프로세스 재시작 시 인메모리 큐는 사라지므로, 남은 pending/running은 기동 시
`fail_orphan_sources`로 정리한다(main.lifespan).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

# 전역 동시 인덱싱 상한 (여러 유저 동시 처리 폭주 방지)
_GLOBAL_MAX_CONCURRENT = 3


class IndexerService:
    def __init__(self) -> None:
        # 유저별 직렬화 락 — 같은 유저는 한 번에 하나만 인덱싱
        self._locks: dict[str, asyncio.Lock] = {}
        # fire-and-forget 태스크 강한 참조 유지 (GC 수거 방지)
        self._bg_tasks: set[asyncio.Task[None]] = set()
        self._semaphore = asyncio.Semaphore(_GLOBAL_MAX_CONCURRENT)

    def _lock_for(self, user_id: str) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        return lock

    def enqueue(
        self,
        user_id: str,
        source_id: str,
        user_email: str,
        runner: Callable[[], Awaitable[None]],
    ) -> None:
        """인덱싱 작업을 큐에 등록. 유저별 락으로 순차 실행된다.

        runner: 실제 인덱싱만 수행하는 async 콜러블 (run_analysis / run_drive_takeout).
        소스는 호출 전 이미 pending으로 생성돼 있어야 한다.
        인덱싱 성공 후 profile-once 정책에 따라 마지막 파일에서만 프로파일러를 돌린다.
        """
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._run(user_id, source_id, user_email, runner))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _run(
        self,
        user_id: str,
        source_id: str,
        user_email: str,
        runner: Callable[[], Awaitable[None]],
    ) -> None:
        from app.services.analysis_source_service import (
            fail_source_async,
            mark_source_running_async,
        )

        async with self._semaphore:
            # 같은 유저의 앞선 인덱싱이 끝날 때까지 대기 (pending 유지)
            async with self._lock_for(user_id):
                await mark_source_running_async(source_id)
                try:
                    await runner()
                except Exception:
                    logger.exception("[Indexer] 실행 실패 source_id=%s", source_id)
                    await fail_source_async(source_id)
                    return
                # 인덱싱 성공 → profile-once 조정 (락 보유 중 = 다음 파일 시작 전)
                await self._finalize_indexing(user_id, source_id, user_email)

    async def _finalize_indexing(
        self, user_id: str, source_id: str, user_email: str
    ) -> None:
        """인덱싱 완료 후: 대기 파일이 남았으면 인덱싱만 완료 처리, 마지막이면 프로파일 1회.

        여러 파일을 한 번에 올려도 '분류 다 끝난 뒤 최근 2달 기록으로 딱 1번' 분석되게 한다.
        """
        from app.core.database.session import AsyncSessionLocal
        from app.models.user_analysis_source import (
            AnalysisSourceStage,
            AnalysisSourceStatus,
            UserAnalysisSource,
        )
        from app.repositories.analysis_source_repository import count_pending_sources
        from app.services.analysis_source_service import set_source_stage_async

        async with AsyncSessionLocal() as session:
            src = await session.get(UserAnalysisSource, uuid.UUID(source_id))
            this_failed = src is None or src.status == AnalysisSourceStatus.FAILED
            pending = await count_pending_sources(session, uuid.UUID(user_id))

        if this_failed:
            # runner가 이미 실패 처리 → 완료/프로파일 하지 않음
            logger.info("[Indexer] 인덱싱 실패 — 프로파일 스킵 source_id=%s", source_id)
            return
        if pending > 0:
            # 아직 인덱싱할 파일 남음 → 이 소스는 '분류 완료(indexed)'로 두고 배치 분석 대기
            await set_source_stage_async(source_id, AnalysisSourceStage.INDEXED)
            logger.info(
                "[Indexer] 분류 완료(대기 %d건 남음) — 배치 분석 대기 source_id=%s",
                pending,
                source_id,
            )
        else:
            # 마지막 인덱싱 → 이 소스로 프로파일러 1회 (전체 catalog·최근 2달 기준)
            from app.services.profiler.service import profiler_service

            await set_source_stage_async(source_id, AnalysisSourceStage.PROFILING)
            profiler_service.enqueue_for_user(
                user_id, user_email, analysis_source_id=source_id
            )
            logger.info(
                "[Indexer] 마지막 인덱싱 완료 — 프로파일 1회 실행 source_id=%s",
                source_id,
            )


indexer_service = IndexerService()
