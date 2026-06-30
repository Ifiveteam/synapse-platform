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
from app.models.user_analysis_source import AnalysisSourceStage
from app.models.user_token import UserToken
from app.repositories.analysis_source_repository import begin_source
from app.services.analysis_source_service import (
    drive_source_key,
    fail_source_async,
    set_source_stage_async,
)
from app.services.takeout_service import (
    download_drive_file,
    find_takeout_in_folder,
    run_takeout_pipeline,
)

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


async def _process_file(user: User, file_id: str, file_name: str | None) -> None:
    source_key = drive_source_key(file_id)
    async with AsyncSessionLocal() as session:
        row, action = await begin_source(session, user.id, source_key, file_name)
        await session.commit()
        source_id = str(row.id)
    if action != "run":
        return  # 이미 처리됨/진행중 → 멱등 스킵

    # 분류
    path = await download_drive_file(file_id, user)
    if not path:
        await fail_source_async(source_id)
        return
    result = await run_takeout_pipeline(path, user_id=user.id)
    if result.get("error"):
        logger.warning(
            "[scheduler] pipeline 오류 file=%s: %s", file_id, result["error"]
        )
        await fail_source_async(source_id)
        return

    # 분석
    await set_source_stage_async(source_id, AnalysisSourceStage.PROFILING)
    from app.services.profiler.service import profiler_service

    profiler_service.enqueue_for_user(
        str(user.id), user.email, analysis_source_id=source_id
    )
    logger.info("[scheduler] 분석 시작 user=%s file=%s", user.id, file_name)


async def _process_user(user: User, folder_id: str) -> None:
    files = await find_takeout_in_folder(user, folder_id)
    for f in files:
        try:
            await _process_file(user, f["id"], f.get("name"))
        except Exception:
            logger.exception(
                "[scheduler] 파일 처리 실패 user=%s file=%s", user.id, f.get("id")
            )


async def _bump_next(user_id) -> None:
    """다음 분석 가능 시점 = 2개월 뒤 달의 1일."""
    async with AsyncSessionLocal() as session:
        db_user = await session.get(User, user_id)
        if db_user:
            db_user.next_analysis_at = first_of_month_ahead(
                datetime.now(timezone.utc), ANALYSIS_INTERVAL_MONTHS
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
