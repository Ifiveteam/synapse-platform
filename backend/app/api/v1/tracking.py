"""익스텐션 유저 행동 데이터 수집 API."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user_dep
from app.core.database.session import get_db
from app.models.behavior import UserBehaviorLog
from app.models.user import User
from app.schemas.behavior import (
    BehaviorLogCreate,
    BehaviorLogItem,
    BehaviorLogListResponse,
    DomainDurationStat,
    TodayStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["Tracking"])

KST = timezone(timedelta(hours=9))


def _clean_url_and_extract_domain(url: str) -> tuple[str, str]:
    """쿼리·fragment 제거 및 path trailing slash 정규화 후 hostname을 반환한다."""
    try:
        parsed = urlparse(url.strip())
        hostname = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise ValueError("scheme 또는 hostname이 유효하지 않습니다")

        path = parsed.path.rstrip("/") or "/"
        cleaned_url = f"{parsed.scheme}://{parsed.netloc}{path}"
        return cleaned_url, hostname[:255]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="유효하지 않은 URL 형식이거나 파싱할 수 없습니다.",
        ) from None
    except Exception:
        logger.exception("[Tracking API] URL 파싱 실패 url=%r", url)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="유효하지 않은 URL 형식이거나 파싱할 수 없습니다.",
        ) from None


def _today_range_kst() -> tuple[datetime, datetime]:
    """오늘 00:00 ~ 내일 00:00 (KST) 구간을 UTC aware datetime으로 반환한다."""
    now = datetime.now(KST)
    start = datetime.combine(now.date(), time.min, tzinfo=KST)
    end = start + timedelta(days=1)
    return start, end


@router.get("/events", response_model=BehaviorLogListResponse)
async def list_behavior_events(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> BehaviorLogListResponse:
    """인증 유저의 최근 행동 로그를 최신순으로 반환한다."""
    result = await session.execute(
        select(UserBehaviorLog)
        .where(UserBehaviorLog.user_id == user.id)
        .order_by(desc(UserBehaviorLog.timestamp), desc(UserBehaviorLog.id))
        .limit(limit)
    )
    logs = result.scalars().all()
    return BehaviorLogListResponse(
        items=[BehaviorLogItem.model_validate(log) for log in logs]
    )


@router.get("/stats/today", response_model=TodayStatsResponse)
async def get_today_behavior_stats(
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> TodayStatsResponse:
    """오늘(KST) 유저의 총 체류 시간과 도메인 TOP 5를 집계한다."""
    start, end = _today_range_kst()
    base_filter = (
        UserBehaviorLog.user_id == user.id,
        UserBehaviorLog.timestamp >= start,
        UserBehaviorLog.timestamp < end,
    )

    total_result = await session.execute(
        select(func.coalesce(func.sum(UserBehaviorLog.duration_seconds), 0)).where(
            *base_filter
        )
    )
    total_duration_seconds = int(total_result.scalar_one())

    domain_result = await session.execute(
        select(
            UserBehaviorLog.domain,
            func.sum(UserBehaviorLog.duration_seconds).label("duration_seconds"),
        )
        .where(*base_filter)
        .group_by(UserBehaviorLog.domain)
        .order_by(desc("duration_seconds"))
        .limit(5)
    )
    top_domains = [
        DomainDurationStat(
            name=row.domain,
            value=int(row.duration_seconds),
            duration_seconds=int(row.duration_seconds),
        )
        for row in domain_result.all()
    ]

    return TodayStatsResponse(
        total_duration_seconds=total_duration_seconds,
        top_domains=top_domains,
    )


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_behavior_event(
    payload: BehaviorLogCreate,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """인증된 유저의 페이지 체류 세션을 영속화한다."""
    cleaned_url, domain = _clean_url_and_extract_domain(payload.url)

    log = UserBehaviorLog(
        user_id=user.id,
        url=cleaned_url,
        domain=domain,
        page_title=payload.page_title,
        duration_seconds=payload.duration_seconds,
        timestamp=payload.timestamp,
    )

    try:
        session.add(log)
        await session.commit()
        await session.refresh(log)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "[Tracking API] DB 적재 실패 user_id=%s url=%r",
            user.id,
            cleaned_url,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="행동 데이터를 저장하는 중 서버 내부 오류가 발생했습니다.",
        ) from None

    return {"id": log.id}
