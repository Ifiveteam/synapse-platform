"""어그리게이터 배치 — 플랫폼 전역 윈도우 조회·스냅샷 저장."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.agents.navigator.constants import BEHAVIOR_AXES
from app.models.behavior import UserBehaviorLog
from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.models.scrap import Scrap
from app.models.user_profile_history import UserProfileHistory
from app.models.user_watch_catalog import UserWatchCatalog
from app.utils.trend_nlp_engine import DEFAULT_TOP_N, TrendNLPEngine

# 플랫폼 일별 배치 기준 타임존 — tracking API·익스텐션 수집과 동일(KST).
KST = timezone(timedelta(hours=9))


def day_window_kst(target: date) -> tuple[datetime, datetime]:
    """대상 일자 [00:00, 다음날 00:00) KST — DB UTC 타임스탬프와 직접 비교 가능."""
    start = datetime.combine(target, time.min, tzinfo=KST)
    end = start + timedelta(days=1)
    return start, end


def yesterday_kst() -> date:
    """KST 기준 어제 날짜."""
    return (datetime.now(KST) - timedelta(days=1)).date()


def day_window_utc(target: date) -> tuple[datetime, datetime]:
    """대상 일자 [00:00, 다음날 00:00) UTC 반환. (레거시·테스트용)"""
    start = datetime.combine(target, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


def yesterday_utc() -> date:
    return (datetime.now(tz=UTC) - timedelta(days=1)).date()


async def fetch_scraps_chunk(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    *,
    offset: int,
    limit: int,
) -> list[Scrap]:
    result = await session.execute(
        select(Scrap)
        .where(
            Scrap.created_at >= window_start,
            Scrap.created_at < window_end,
        )
        .order_by(Scrap.created_at, Scrap.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def fetch_behavior_logs_chunk(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    *,
    offset: int,
    limit: int,
) -> list[UserBehaviorLog]:
    result = await session.execute(
        select(UserBehaviorLog)
        .where(
            UserBehaviorLog.timestamp >= window_start,
            UserBehaviorLog.timestamp < window_end,
        )
        .order_by(UserBehaviorLog.timestamp, UserBehaviorLog.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def fetch_watch_catalog_chunk(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    *,
    offset: int,
    limit: int,
) -> list[UserWatchCatalog]:
    result = await session.execute(
        select(UserWatchCatalog)
        .options(joinedload(UserWatchCatalog.analysis))
        .where(
            UserWatchCatalog.watched_at >= window_start,
            UserWatchCatalog.watched_at < window_end,
        )
        .order_by(UserWatchCatalog.watched_at, UserWatchCatalog.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.unique().scalars().all())


async def fetch_latest_profile_per_user(
    session: AsyncSession,
) -> list[UserProfileHistory]:
    """유저별 최신 프로파일 스냅샷 — PostgreSQL DISTINCT ON (user_id)."""
    result = await session.execute(
        select(UserProfileHistory)
        .distinct(UserProfileHistory.user_id)
        .order_by(
            UserProfileHistory.user_id,
            UserProfileHistory.snapshot_date.desc(),
        )
    )
    return list(result.scalars().all())


async def fetch_historical_daily_keyword_counts(
    session: AsyncSession,
    target_date: date,
    *,
    lookback_days: int = 7,
) -> list[dict[str, int]]:
    """지난 lookback_days 일간 스냅샷에서 일별 명사 빈도(daily_counts) 조회.

    target_date 이전 날짜만 포함한다 (당일 제외).
    스냅샷이 없는 날은 빈 dict로 패딩하지 않고 실제 존재하는 일자만 반환한다.
    """
    if lookback_days <= 0:
        return []

    history_start = target_date - timedelta(days=lookback_days)
    window_start = datetime.combine(history_start, time.min, tzinfo=KST)
    window_end = datetime.combine(target_date, time.min, tzinfo=KST)

    result = await session.execute(
        select(GlobalTrendsSnapshot)
        .where(
            GlobalTrendsSnapshot.snapshot_date >= window_start,
            GlobalTrendsSnapshot.snapshot_date < window_end,
        )
        .order_by(GlobalTrendsSnapshot.snapshot_date.asc())
    )
    rows = list(result.scalars().all())

    daily_histories: list[dict[str, int]] = []
    for row in rows:
        payload = row.trending_keywords or {}
        raw_counts = payload.get("daily_counts")
        if isinstance(raw_counts, dict):
            daily_histories.append(
                {str(k): int(v) for k, v in raw_counts.items() if int(v) > 0}
            )
        else:
            daily_histories.append({})

    return daily_histories


async def build_trending_keywords_payload(
    session: AsyncSession,
    *,
    target_date: date,
    refined_keywords: list[str],
    nlp_engine: TrendNLPEngine | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> dict[str, Any]:
    """에이전트 정제 키워드 → 7일 이동평균 대비 급상승 랭킹 JSONB."""
    engine = nlp_engine or TrendNLPEngine()
    today_counts = engine.build_daily_counts(refined_keywords)

    historical_daily = await fetch_historical_daily_keyword_counts(
        session,
        target_date,
        lookback_days=7,
    )

    payload = engine.build_ranking(
        today_counts,
        historical_daily,
        top_n=top_n,
    )
    payload["target_date"] = target_date.isoformat()
    return payload


async def insert_global_trends_snapshot(
    session: AsyncSession,
    *,
    snapshot_date: datetime,
    top_domains: dict,
    top_scrap_categories: dict,
    external_market_keywords: dict,
    global_8_axis_avg: dict,
    trending_keywords: dict | None = None,
    keyword_context_map: dict | None = None,
    cross_domain_insights: dict | None = None,
) -> GlobalTrendsSnapshot:
    row = GlobalTrendsSnapshot(
        snapshot_date=snapshot_date,
        top_domains=top_domains,
        top_scrap_categories=top_scrap_categories,
        external_market_keywords=external_market_keywords,
        global_8_axis_avg=global_8_axis_avg,
        trending_keywords=trending_keywords or {},
        keyword_context_map=keyword_context_map or {},
        cross_domain_insights=cross_domain_insights,
    )
    session.add(row)
    await session.flush()
    return row


def compute_global_8_axis_average(
    profiles: Sequence[UserProfileHistory],
) -> dict[str, float]:
    """유저별 최신 프로파일에서 플랫폼 8축 평균 산출."""
    sums = {axis: 0.0 for axis in BEHAVIOR_AXES}
    counts = {axis: 0 for axis in BEHAVIOR_AXES}

    for profile in profiles:
        for axis in BEHAVIOR_AXES:
            value = getattr(profile, axis, None)
            if value is None:
                continue
            sums[axis] += float(value)
            counts[axis] += 1

    return {
        axis: round(sums[axis] / counts[axis], 4) if counts[axis] else 0.0
        for axis in BEHAVIOR_AXES
    }


def empty_top_domains_template() -> dict[str, dict[str, int | str | float]]:
    from app.models.trend_domain import TrendDomain

    return {
        domain.value: {
            "user_count": 0,
            "total_duration": 0,
            "main_category": domain.value,
            "avg_weight": 0.0,
        }
        for domain in TrendDomain
    }
