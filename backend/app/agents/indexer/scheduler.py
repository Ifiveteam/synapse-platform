"""Celery tasks — 주간 가중치 재계산."""

import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.agents.indexer.scheduler.update_weights_task", bind=True)
def update_weights_task(self):
    """매주 월요일 03:00 KST — 시청일 기준 decay 가중치 전체 재계산."""
    try:
        asyncio.run(_update_weights())
    except Exception as exc:
        logger.error("[Scheduler] 가중치 업데이트 실패: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300, max_retries=3) from exc


async def _update_weights():
    from app.core.database.session import AsyncSessionLocal
    from app.repositories.indexer_repository import update_all_weights

    async with AsyncSessionLocal() as session:
        count = await update_all_weights(session)
    logger.info("[Scheduler] 가중치 업데이트 완료: %d건", count)
