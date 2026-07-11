"""어그리게이터(4 에이전트) 일별 배치 스케줄러.

플랫폼 전역 트렌드 집계를 주기적으로 실행한다.
- 루프는 TICK마다 깨어나 run_daily_aggregation_job()을 1회 호출한다.

dev: AGGREGATOR_SCHEDULER_TICK_SECONDS로 tick을 줄여 빠르게 테스트 가능.
수동 실행: POST /api/v1/aggregator/trigger?date_str=YYYY-MM-DD
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date

from app.workers.aggregator_worker import run_aggregation_pipeline

logger = logging.getLogger("app.services.aggregator_scheduler")

TICK_SECONDS = int(os.getenv("AGGREGATOR_SCHEDULER_TICK_SECONDS", "86400"))  # 기본 하루
STARTUP_DELAY_SECONDS = 10  # 부팅 직후 DB 준비 대기 (startup race 방지)
ERROR_RETRY_SECONDS = 60  # tick 실패 시 빠른 재시도 (하루 대기 방지)

# 수동 트리거·fire-and-forget 태스크 강한 참조 (GC 수거 방지)
_bg_tasks: set[asyncio.Task[None]] = set()


async def run_daily_aggregation_job(target_date: date | None = None) -> None:
    """일별 거시 트렌드 배치 집계 — 단일 실행 단위."""
    label = target_date.isoformat() if target_date else "yesterday(KST)"
    logger.info("[aggregator] 새벽 배치 집계 프로세스 시작 target=%s", label)
    try:
        await run_aggregation_pipeline(target_date=target_date)
    except Exception:
        logger.exception("[aggregator] 배치 집계 프로세스 실패 target=%s", label)
        raise

    logger.info("[aggregator] 새벽 배치 집계 프로세스 완료 target=%s", label)


def enqueue_daily_aggregation(target_date: date | None = None) -> None:
    """배치 집계를 백그라운드 태스크로 1회 등록한다 (수동 트리거·fire-and-forget)."""
    loop = asyncio.get_running_loop()
    task = loop.create_task(run_daily_aggregation_job(target_date))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


async def scheduler_loop() -> None:
    logger.info("[aggregator] 스케줄러 시작 (tick=%ds)", TICK_SECONDS)
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        delay = TICK_SECONDS
        try:
            await run_daily_aggregation_job()
        except asyncio.CancelledError:
            logger.info("[aggregator] 스케줄러 종료")
            raise
        except Exception:
            logger.exception(
                "[aggregator] tick 실패 — %ds 후 재시도", ERROR_RETRY_SECONDS
            )
            delay = min(TICK_SECONDS, ERROR_RETRY_SECONDS)
        await asyncio.sleep(delay)
