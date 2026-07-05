"""재생목록 자동 갱신 백그라운드 스케줄러.

- refresh_period(weekly/monthly)가 설정된 재생목록을, 주기가 지나면 **전체 재생성**
  (_generate_playlist_bg = 채널 재발굴→RSS→큐레이션)한다. "매일"은 지원 안 함(쿼터).
- tick마다 깨어나 last_refreshed_at 기준으로 도래한 것만 처리. **순차 + tick당 상한**
  으로 YouTube 쿼터를 보호한다.
- 서버가 떠 있을 때만 동작. 다중 인스턴스면 중복 실행 주의(개발 단일은 무관).

dev: PLAYLIST_REFRESH_TICK_SECONDS로 tick을 줄여 빠르게 테스트 가능.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database.session import AsyncSessionLocal
from app.models.navigator_playlist import NavigatorPlaylist

logger = logging.getLogger("app.services.playlist_refresh_scheduler")

TICK_SECONDS = int(os.getenv("PLAYLIST_REFRESH_TICK_SECONDS", "3600"))  # 기본 1시간
STARTUP_DELAY_SECONDS = 15  # 부팅 직후 DB 준비 대기
ERROR_RETRY_SECONDS = 120  # tick 실패 시 빠른 재시도
MAX_PER_TICK = 5  # tick당 최대 재생성 개수 (쿼터 버스트 방지)

_PERIOD_DAYS = {"weekly": 7, "monthly": 30}


def _is_due(period: str, last: datetime | None, now: datetime) -> bool:
    """주기(weekly/monthly)가 지났으면 True. 아직 갱신 안 됐으면(None) 대상."""
    days = _PERIOD_DAYS.get(period)
    if days is None:
        return False
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return now - last >= timedelta(days=days)


async def _due_playlists() -> list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]]:
    """주기 도래한 (user_id, ideal_id, playlist_id) — 최대 MAX_PER_TICK개."""
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(NavigatorPlaylist).where(
                NavigatorPlaylist.refresh_period.in_(["weekly", "monthly"]),
                NavigatorPlaylist.status == "ready",
            )
        )
        rows = list(result.scalars().all())
    due = [
        (r.user_id, r.ideal_id, r.id)
        for r in rows
        if _is_due(r.refresh_period, r.last_refreshed_at, now)
    ]
    return due[:MAX_PER_TICK]


async def run_once() -> None:
    # 순환 임포트 방지 — 사용 시점에 임포트
    from app.services.navigator.service import _generate_playlist_bg

    due = await _due_playlists()
    if due:
        logger.info("[playlist-scheduler] 갱신 대상 %d개", len(due))
    for user_id, ideal_id, playlist_id in due:
        try:
            # 전체 재생성(재발굴). 완료 시 last_refreshed_at이 갱신돼 다음 주기까지 대기.
            await _generate_playlist_bg(
                user_id=user_id, ideal_id=ideal_id, playlist_id=playlist_id
            )
        except Exception:
            logger.exception(
                "[playlist-scheduler] 재생성 실패 playlist=%s", playlist_id
            )


async def scheduler_loop() -> None:
    logger.info("[playlist-scheduler] 시작 (tick=%ds)", TICK_SECONDS)
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        delay = TICK_SECONDS
        try:
            await run_once()
        except asyncio.CancelledError:
            logger.info("[playlist-scheduler] 종료")
            raise
        except Exception:
            logger.exception(
                "[playlist-scheduler] tick 실패 — %ds 후 재시도", ERROR_RETRY_SECONDS
            )
            delay = min(TICK_SECONDS, ERROR_RETRY_SECONDS)
        await asyncio.sleep(delay)
