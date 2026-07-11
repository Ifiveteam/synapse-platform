"""과거 Raw가 있는 일자에 Aggregator 스냅샷을 백필한다."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# `uv run python scripts/...` 실행 시 backend 루트를 path에 넣는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.core.database.session import AsyncSessionLocal
from app.models.behavior import UserBehaviorLog
from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.models.scrap import Scrap
from app.models.user_watch_catalog import UserWatchCatalog
from app.repositories.aggregator_repository import day_window_kst
from app.workers.aggregator_worker import run_aggregation_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_snapshots")

# watch만 아주 적은 날까지 전부 돌리면 LLM 비용·시간이 큼.
MIN_WATCH_COUNT = 10


async def discover_target_dates() -> list[date]:
    by: dict[date, dict[str, int]] = defaultdict(
        lambda: {"scrap": 0, "behavior": 0, "watch": 0}
    )
    async with AsyncSessionLocal() as session:
        for _model, col, key in (
            (Scrap, Scrap.created_at, "scrap"),
            (UserBehaviorLog, UserBehaviorLog.timestamp, "behavior"),
            (UserWatchCatalog, UserWatchCatalog.watched_at, "watch"),
        ):
            day_col = func.date(func.timezone("Asia/Seoul", col))
            result = await session.execute(
                select(day_col, func.count()).group_by(day_col)
            )
            for day_value, count in result.all():
                if day_value is None:
                    continue
                day = (
                    day_value
                    if isinstance(day_value, date)
                    else date.fromisoformat(str(day_value))
                )
                by[day][key] = int(count)

    targets: list[date] = []
    for day in sorted(by.keys()):
        counts = by[day]
        if counts["scrap"] > 0 or counts["behavior"] > 0:
            targets.append(day)
            logger.info(
                "include %s scrap=%d behavior=%d watch=%d",
                day,
                counts["scrap"],
                counts["behavior"],
                counts["watch"],
            )
        elif counts["watch"] >= MIN_WATCH_COUNT:
            targets.append(day)
            logger.info(
                "include %s watch=%d (threshold)",
                day,
                counts["watch"],
            )
        else:
            logger.info(
                "skip %s scrap=%d behavior=%d watch=%d",
                day,
                counts["scrap"],
                counts["behavior"],
                counts["watch"],
            )
    return targets


async def has_internal_snapshot(target: date) -> bool:
    """이미 scrap/behavior/youtube 맥락이 있는 스냅샷이 있으면 스킵."""
    start, end = day_window_kst(target)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GlobalTrendsSnapshot)
            .where(
                GlobalTrendsSnapshot.snapshot_date >= start,
                GlobalTrendsSnapshot.snapshot_date < end,
            )
            .order_by(GlobalTrendsSnapshot.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
    if row is None:
        return False
    contexts = (row.keyword_context_map or {}).get("contexts") or []
    internal = {"scrap", "youtube", "behavior", "user_daily"}
    return any(
        isinstance(ctx, dict) and ctx.get("source") in internal for ctx in contexts
    )


async def main() -> None:
    targets = await discover_target_dates()
    logger.info("candidate targets=%d %s", len(targets), targets)
    for index, target in enumerate(targets, start=1):
        if await has_internal_snapshot(target):
            logger.info(
                "[%d/%d] skip %s (internal snapshot exists)",
                index,
                len(targets),
                target,
            )
            continue
        logger.info("[%d/%d] aggregating %s", index, len(targets), target)
        try:
            await run_aggregation_pipeline(target_date=target)
            logger.info("[%d/%d] done %s", index, len(targets), target)
        except Exception:
            logger.exception("[%d/%d] failed %s", index, len(targets), target)


if __name__ == "__main__":
    asyncio.run(main())
