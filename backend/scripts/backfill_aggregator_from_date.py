"""배포 서버용 — 지정 시작일(기본 2026-07-01)부터 어제(KST)까지 Aggregator 백필.

사용:
  cd backend
  uv run python scripts/backfill_aggregator_from_date.py
  uv run python scripts/backfill_aggregator_from_date.py --start 2026-07-01
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.aggregator_repository import yesterday_kst
from app.workers.aggregator_worker import run_aggregation_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_from_date")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregator date-range backfill")
    parser.add_argument(
        "--start",
        default="2026-07-01",
        help="시작일 YYYY-MM-DD (기본 2026-07-01)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="종료일 YYYY-MM-DD (기본: KST 어제)",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else yesterday_kst()
    if end < start:
        logger.error("end(%s) < start(%s)", end, start)
        return

    days = (end - start).days + 1
    logger.info("backfill range %s .. %s (%d days)", start, end, days)
    current = start
    index = 0
    while current <= end:
        index += 1
        logger.info("[%d/%d] aggregating %s", index, days, current)
        try:
            await run_aggregation_pipeline(target_date=current)
            logger.info("[%d/%d] done %s", index, days, current)
        except Exception:
            logger.exception("[%d/%d] failed %s", index, days, current)
        current += timedelta(days=1)


if __name__ == "__main__":
    asyncio.run(main())
