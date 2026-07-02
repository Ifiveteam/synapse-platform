"""Takeout 자동 분석 백그라운드 스케줄러.

연동된 Drive 폴더를 주기적으로 스캔해 새 Takeout zip을 무인 분석한다.
- 루프는 TICK마다 깨어나고, 유저는 next_analysis_at이 지났을 때만 처리(월 1회).
- 멱등: 이미 처리한 file_id는 analysis_source(begin_source)가 걸러줌.
- 분류/분석 단계는 set_source_stage_async로 기록 → 목록에 "분류중/분석중" 표시.
- 토큰 만료는 download/조회의 401 자동 갱신(google_refresh_token)으로 처리.

dev: TAKEOUT_SCHEDULER_TICK_SECONDS로 tick을 줄여 빠르게 테스트 가능.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.user_token import UserToken
from app.repositories.analysis_source_repository import begin_source
from app.services.analysis_source_service import drive_source_key
from app.services.takeout_service import find_takeout_in_folder

logger = logging.getLogger("app.services.takeout_scheduler")

TICK_SECONDS = int(os.getenv("TAKEOUT_SCHEDULER_TICK_SECONDS", "86400"))  # 기본 하루
STARTUP_DELAY_SECONDS = 10  # 부팅 직후 DB 준비 대기 (startup race 방지)
ERROR_RETRY_SECONDS = 60  # tick 실패 시 빠른 재시도 (하루 대기 방지)

ANALYSIS_INTERVAL_MONTHS = 2  # 마지막 분석으로부터 2개월 경과 시에만 재분석


def first_of_month_ahead(now: datetime, months: int) -> datetime:
    """now로부터 months개월 뒤 달의 1일 00:00 UTC."""
    idx = now.year * 12 + (now.month - 1) + months
    year, month0 = divmod(idx, 12)
    return datetime(year, month0 + 1, 1, tzinfo=timezone.utc)


async def _due_users() -> list[tuple[User, str]]:
    """drive_folder_id 연동 + next_analysis_at 지난 유저."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User, UserToken.drive_folder_id)
            .join(UserToken, UserToken.user_id == User.id)
            .where(
                UserToken.drive_folder_id.isnot(None),
                User.next_analysis_at <= now,
            )
        )
        return [(row[0], row[1]) for row in result.all()]


async def _process_file(
    user: User, file_id: str, file_name: str | None, batch_id: str
) -> None:
    """새 파일을 멱등 등록 후 유저별 직렬 큐에 넣는다(이번 실행 배치에 소속).

    수동 경로(직접/전체/선택 분석)와 **동일**하게 IndexerService를 태워, 이번 실행에
    수집한 파일 전체를 순차 분류한 뒤 배치가 seal되면 프로파일러를 1회만 돌린다.
    """
    import uuid as uuid_mod

    from app.api.v1.takeout import run_drive_takeout
    from app.services.indexer_service import indexer_service

    source_key = drive_source_key(file_id)
    async with AsyncSessionLocal() as session:
        row, action = await begin_source(
            session, user.id, source_key, file_name, batch_id=batch_id
        )
        await session.commit()
        source_id = str(row.id)
    if action != "queued":
        return  # 이미 완료/진행중/대기중 → 멱등 스킵

    task_id = str(uuid_mod.uuid4())
    indexer_service.enqueue(
        str(user.id),
        source_id,
        user.email,
        lambda: run_drive_takeout(task_id, file_id, user, source_id),
    )
    logger.info("[scheduler] 큐 등록 user=%s file=%s", user.id, file_name)


async def _process_user(user: User, folder_id: str) -> None:
    import uuid as uuid_mod

    from app.services.analysis_source_service import seal_batch_async

    files = await find_takeout_in_folder(user, folder_id)
    if not files:
        return
    # 이번 스케줄 실행 = 한 배치. 파일 전부 등록 후 seal("다 보냄").
    batch_id = str(uuid_mod.uuid4())
    for f in files:
        try:
            await _process_file(user, f["id"], f.get("name"), batch_id)
        except Exception:
            logger.exception(
                "[scheduler] 파일 처리 실패 user=%s file=%s", user.id, f.get("id")
            )
    await seal_batch_async(user.id, batch_id, user.email)


async def _bump_next(user_id) -> None:
    """다음 분석 가능 시점 = 유저 설정 주기(개월) 뒤 달의 1일."""
    async with AsyncSessionLocal() as session:
        db_user = await session.get(User, user_id)
        if db_user:
            months = db_user.analysis_interval_months or ANALYSIS_INTERVAL_MONTHS
            db_user.next_analysis_at = first_of_month_ahead(
                datetime.now(timezone.utc), months
            )
            await session.commit()


async def run_once() -> None:
    due = await _due_users()
    if due:
        logger.info("[scheduler] 처리 대상 %d명", len(due))
    for user, folder_id in due:
        try:
            await _process_user(user, folder_id)
        except Exception:
            logger.exception("[scheduler] 유저 처리 실패 user=%s", user.id)
        finally:
            await _bump_next(user.id)


async def scheduler_loop() -> None:
    logger.info("[scheduler] Takeout 스케줄러 시작 (tick=%ds)", TICK_SECONDS)
    await asyncio.sleep(STARTUP_DELAY_SECONDS)  # 부팅 직후 DB 준비 대기
    while True:
        delay = TICK_SECONDS
        try:
            await run_once()
        except asyncio.CancelledError:
            logger.info("[scheduler] 종료")
            raise
        except Exception:
            logger.exception(
                "[scheduler] tick 실패 — %ds 후 재시도", ERROR_RETRY_SECONDS
            )
            delay = min(TICK_SECONDS, ERROR_RETRY_SECONDS)
        await asyncio.sleep(delay)
