"""Async DB operations for the indexer (user_watch_catalog)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_source_catalog import AnalysisSourceCatalog
from app.models.user_subscription import UserSubscription
from app.models.user_watch_catalog import UserWatchCatalog
from app.models.video_analysis import VideoAnalysis


def parse_watched_at(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def catalog_row_values(user_id: uuid.UUID, item: dict) -> dict:
    """Pipeline dict → user_watch_catalog insert/update values."""
    watched_at = parse_watched_at(item.get("watched_at"))
    tags = item.get("tags")
    if tags is None and item.get("keywords"):
        tags = item.get("keywords")

    category_id = item.get("youtube_category_id") or item.get("category_id")
    if category_id is not None:
        category_id = str(category_id)[:10]

    duration = item.get("duration_sec")
    if duration is None:
        duration = item.get("duration")

    return {
        "user_id": user_id,
        "platform": item.get("platform") or "youtube",
        "channel": item.get("channel") or "unknown",
        "channel_url": item.get("channel_url"),
        "title": item.get("title"),
        "url": item.get("url"),
        "watched_at": watched_at,
        "watch_count": item.get("watch_count") or 1,
        "youtube_category_id": category_id,
        "duration_sec": duration,
        "is_shorts": item.get("is_shorts"),
        "description": item.get("description"),
        "tags": tags,
        "thumbnail_url": item.get("thumbnail_url"),
        "embedding_text": item.get("embedding_text"),
        "embedding": item.get("embedding"),
    }


_UPSERT_COLUMNS = (
    "platform",
    "channel",
    "channel_url",
    "title",
    "watched_at",
    "watch_count",
    "youtube_category_id",
    "duration_sec",
    "is_shorts",
    "description",
    "tags",
    "thumbnail_url",
    "embedding_text",
    "embedding",
)


async def upsert_catalog_records(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[dict],
) -> int:
    """Bulk upsert into user_watch_catalog. UNIQUE (user_id, url)."""
    count = 0
    for item in items:
        if not item.get("url"):
            continue
        values = catalog_row_values(user_id, item)
        insert_stmt = pg_insert(UserWatchCatalog).values(**values)
        stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_uwc_user_url",
            set_={col: getattr(insert_stmt.excluded, col) for col in _UPSERT_COLUMNS},
        )
        await session.execute(stmt)
        count += 1
    return count


async def link_source_catalog(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_id: uuid.UUID | str | None,
    urls: list[str],
) -> int:
    """이 파일(source)에 속한 영상들의 소속 짝을 analysis_source_catalog에 기록.

    신규+기존 영상 URL 전부를 받아 catalog_id로 해석 후 (source, catalog) 짝을 넣는다.
    같은 영상이 여러 파일에 겹쳐도 짝이 별도 행으로 남는다(on conflict do nothing).
    배치 스코프 분석이 이 표를 조인해 그 파일들의 영상만 골라낸다.
    """
    if source_id is None:
        return 0
    clean_urls = [u for u in urls if u]
    if not clean_urls:
        return 0
    sid = uuid.UUID(str(source_id))
    rows = await session.execute(
        select(UserWatchCatalog.id).where(
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.url.in_(clean_urls),
        )
    )
    catalog_ids = [row[0] for row in rows.all()]
    if not catalog_ids:
        return 0
    stmt = (
        pg_insert(AnalysisSourceCatalog)
        .values([{"analysis_source_id": sid, "catalog_id": cid} for cid in catalog_ids])
        .on_conflict_do_nothing(constraint="uq_asc_source_catalog")
    )
    await session.execute(stmt)
    return len(catalog_ids)


async def fetch_indexed_urls(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> set[str]:
    """이미 임베딩까지 완료된 url 집합 (증분 인덱싱 skip 대상).

    embedding이 NULL인 행(과거 키 부재로 미완성)은 제외 → 자동 백필 대상이 된다.
    """
    rows = await session.execute(
        select(UserWatchCatalog.url).where(
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.embedding.isnot(None),
        )
    )
    return {row[0] for row in rows.all()}


async def update_watch_meta(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[dict],
) -> int:
    """기존 영상의 watched_at·watch_count만 갱신 (enrich·임베딩 미터치).

    재시청·반복시청이 롤링 윈도우/선호 강도에 반영되도록 한다.
    """
    count = 0
    for item in items:
        url = item.get("url")
        if not url:
            continue
        await session.execute(
            update(UserWatchCatalog)
            .where(
                UserWatchCatalog.user_id == user_id,
                UserWatchCatalog.url == url,
            )
            .values(
                watched_at=parse_watched_at(item.get("watched_at")),
                watch_count=item.get("watch_count") or 1,
            )
        )
        count += 1
    return count


async def delete_user_catalog(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    include_analysis: bool = True,
) -> None:
    """Reindex: video_analysis then catalog (FK order)."""
    if include_analysis:
        await session.execute(
            delete(VideoAnalysis).where(VideoAnalysis.user_id == user_id)
        )
    await session.execute(
        delete(UserWatchCatalog).where(UserWatchCatalog.user_id == user_id)
    )


# ---------------------------------------------------------------------------
# 구독정보 (user_subscription)
# ---------------------------------------------------------------------------


async def replace_subscriptions(
    session: AsyncSession,
    user_id: uuid.UUID,
    rows: list[dict],
) -> int:
    """구독 전체 교체 — 기존 삭제 후 이번 스냅샷 insert (구독 취소 반영).

    호출부는 구독 CSV가 실제로 있을 때만 호출한다 (빈 목록으로 교체 금지).
    """
    await session.execute(
        delete(UserSubscription).where(UserSubscription.user_id == user_id)
    )
    count = 0
    seen: set[str] = set()
    for row in rows:
        channel_id = (row.get("channel_id") or "").strip()
        if not channel_id or channel_id in seen:
            continue
        seen.add(channel_id)
        session.add(
            UserSubscription(
                user_id=user_id,
                channel_id=channel_id,
                channel_url=row.get("channel_url"),
                channel_title=row.get("channel_title"),
            )
        )
        count += 1
    await session.flush()
    return count


async def delete_subscriptions(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """유저 구독 전체 삭제 (catalog 초기화 시 동반 삭제)."""
    await session.execute(
        delete(UserSubscription).where(UserSubscription.user_id == user_id)
    )


async def fetch_subscriptions(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[UserSubscription]:
    """유저 구독 채널 전체 (프로파일러·네비게이터 재사용용 읽기)."""
    result = await session.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user_id)
        .order_by(UserSubscription.channel_title)
    )
    return list(result.scalars().all())


async def recent_watched_start(
    session: AsyncSession, user_id: uuid.UUID, window_days: int
) -> datetime | None:
    """유저의 최근 시청(max watched_at) 기준 window_days 전 시각. 기록 없으면 None.

    그래프 뷰 '마지막 시청일 기준 2달' 필터의 시작점. (프로파일러 채점 anchor와 동일 규칙)
    """
    anchor = (
        await session.execute(
            select(func.max(UserWatchCatalog.watched_at)).where(
                UserWatchCatalog.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if anchor is None:
        return None
    return anchor - timedelta(days=window_days)


async def count_catalog(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    since: datetime | None = None,
) -> int:
    conditions = [UserWatchCatalog.user_id == user_id]
    if since is not None:
        conditions.append(UserWatchCatalog.watched_at >= since)
    result = await session.execute(
        select(func.count()).select_from(UserWatchCatalog).where(*conditions)
    )
    return int(result.scalar() or 0)


async def get_all_catalog(
    session: AsyncSession, user_id: uuid.UUID | None = None
) -> list[UserWatchCatalog]:
    query = select(UserWatchCatalog).order_by(UserWatchCatalog.watched_at.desc())
    if user_id is not None:
        query = query.where(UserWatchCatalog.user_id == user_id)
    result = await session.execute(query)
    return list(result.scalars().all())


def _listable_channel_conditions():
    """Placeholder·빈 채널명은 상위 채널 집계에서 제외."""
    trimmed = func.trim(UserWatchCatalog.channel)
    return (
        UserWatchCatalog.channel.isnot(None),
        trimmed != "",
        func.lower(trimmed) != "unknown",
    )


def _source_member_subquery(source_ids: list[uuid.UUID]):
    """배치 소스들에 소속된 catalog_id 집합 (상위 집계 스코프용)."""
    return (
        select(AnalysisSourceCatalog.catalog_id)
        .where(AnalysisSourceCatalog.analysis_source_id.in_(source_ids))
        .distinct()
    )


async def fetch_top_categories(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 5,
    since: datetime | None = None,
    source_ids: list[uuid.UUID] | None = None,
) -> list[dict[str, int | str]]:
    """user_watch_catalog GROUP BY youtube_category_id — 상위 N개.

    source_ids가 주어지면 그 배치 소속 영상만 집계(임베딩 미로드, SQL 집계).
    """
    conditions = [UserWatchCatalog.user_id == user_id]
    if source_ids:
        conditions.append(UserWatchCatalog.id.in_(_source_member_subquery(source_ids)))
    if since is not None:
        conditions.append(UserWatchCatalog.watched_at >= since)
    rows = await session.execute(
        select(UserWatchCatalog.youtube_category_id, func.count())
        .where(*conditions)
        .group_by(UserWatchCatalog.youtube_category_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {"category_id": str(row[0] or "unknown"), "count": int(row[1])}
        for row in rows.all()
    ]


async def fetch_top_channels(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 5,
    since: datetime | None = None,
    source_ids: list[uuid.UUID] | None = None,
    is_shorts: bool | None = None,
) -> list[dict[str, int | str]]:
    """user_watch_catalog GROUP BY channel — 상위 N개.

    source_ids가 주어지면 그 배치 소속 영상만 집계(임베딩 미로드, SQL 집계).
    is_shorts=True면 숏폼만, False면 롱폼만(is_shorts가 True가 아닌 것), None이면 전체.
    """
    conditions = [UserWatchCatalog.user_id == user_id, *_listable_channel_conditions()]
    if source_ids:
        conditions.append(UserWatchCatalog.id.in_(_source_member_subquery(source_ids)))
    if is_shorts is True:
        conditions.append(UserWatchCatalog.is_shorts.is_(True))
    elif is_shorts is False:
        conditions.append(UserWatchCatalog.is_shorts.isnot(True))
    if since is not None:
        conditions.append(UserWatchCatalog.watched_at >= since)
    rows = await session.execute(
        select(UserWatchCatalog.channel, func.count())
        .where(*conditions)
        .group_by(UserWatchCatalog.channel)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {"channel": str(row[0] or "unknown"), "count": int(row[1])}
        for row in rows.all()
    ]


async def fetch_graph_summary(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    category_limit: int = 8,
    channel_limit: int = 10,
    window_days: int | None = None,
) -> dict:
    """그래프 UI용 catalog 집계 — 전체 영상 목록 없이 상위 카테고리·채널만.

    window_days가 주어지면 '마지막 시청일 기준 N일' 이내만 집계.
    """
    since = (
        await recent_watched_start(session, user_id, window_days)
        if window_days
        else None
    )
    total = await count_catalog(session, user_id, since=since)
    categories = await fetch_top_categories(
        session, user_id, limit=category_limit, since=since
    )
    top_channels = await fetch_top_channels(
        session, user_id, limit=channel_limit, since=since
    )

    channels: list[dict[str, int | str]] = []
    for item in top_channels:
        channel_name = str(item["channel"])
        chan_conditions = [
            UserWatchCatalog.user_id == user_id,
            UserWatchCatalog.channel == channel_name,
        ]
        if since is not None:
            chan_conditions.append(UserWatchCatalog.watched_at >= since)
        row = await session.execute(
            select(UserWatchCatalog.youtube_category_id, func.count())
            .where(*chan_conditions)
            .group_by(UserWatchCatalog.youtube_category_id)
            .order_by(func.count().desc())
            .limit(1)
        )
        primary = row.first()
        channels.append(
            {
                "channel": channel_name,
                "count": int(item["count"]),
                "category_id": str(primary[0] or "unknown") if primary else "unknown",
            }
        )

    return {"total": total, "categories": categories, "channels": channels}


async def fetch_catalog_embedding_rows(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    before: datetime | None = None,
    after: datetime | None = None,
    limit: int | None = None,
    source_ids: list[uuid.UUID] | None = None,
) -> list[dict]:
    """임베딩 그래프용 catalog 행 (embedding 있는 것만). 최신 시청순, limit 시 상한.

    source_ids가 주어지면 그 배치 소속 영상(analysis_source_catalog 조인)만.
    """
    conditions = [
        UserWatchCatalog.user_id == user_id,
        UserWatchCatalog.embedding.isnot(None),
    ]
    if source_ids:
        member_subq = (
            select(AnalysisSourceCatalog.catalog_id)
            .where(AnalysisSourceCatalog.analysis_source_id.in_(source_ids))
            .distinct()
        )
        conditions.append(UserWatchCatalog.id.in_(member_subq))
    if before:
        conditions.append(UserWatchCatalog.watched_at < before)
    if after:
        conditions.append(UserWatchCatalog.watched_at >= after)

    query = (
        select(
            UserWatchCatalog.id,
            UserWatchCatalog.title,
            UserWatchCatalog.channel,
            UserWatchCatalog.youtube_category_id,
            UserWatchCatalog.is_shorts,
            UserWatchCatalog.embedding,
        )
        .where(*conditions)
        .order_by(UserWatchCatalog.watched_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    rows = await session.execute(query)
    result: list[dict] = []
    for row in rows.all():
        embedding = row.embedding
        if embedding is None:
            continue
        vector = list(embedding) if not isinstance(embedding, list) else embedding
        if not vector:
            continue
        result.append(
            {
                "id": row.id,
                "title": row.title,
                "channel": row.channel,
                "youtube_category_id": row.youtube_category_id,
                "is_shorts": row.is_shorts,
                "embedding": vector,
            }
        )
    return result


async def compute_catalog_stats(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """UI 집계 — catalog 쿼리만 사용."""
    total = await count_catalog(session, user_id)

    if total == 0:
        return {
            "total": 0,
            "shorts_count": 0,
            "long_count": 0,
            "category_stats": {},
            "channel_top5": [],
        }

    shorts_q = (
        select(func.count())
        .select_from(UserWatchCatalog)
        .where(
            UserWatchCatalog.user_id == user_id, UserWatchCatalog.is_shorts.is_(True)
        )
    )
    shorts_count = (await session.execute(shorts_q)).scalar() or 0

    cat_rows = await session.execute(
        select(UserWatchCatalog.youtube_category_id, func.count())
        .where(UserWatchCatalog.user_id == user_id)
        .group_by(UserWatchCatalog.youtube_category_id)
        .order_by(func.count().desc())
    )
    category_stats = {(row[0] or "unknown"): row[1] for row in cat_rows.all()}

    ch_rows = await session.execute(
        select(UserWatchCatalog.channel, func.count())
        .where(UserWatchCatalog.user_id == user_id, *_listable_channel_conditions())
        .group_by(UserWatchCatalog.channel)
        .order_by(func.count().desc())
        .limit(5)
    )
    channel_top5 = [{"name": row[0], "count": row[1]} for row in ch_rows.all()]

    return {
        "total": total,
        "shorts_count": shorts_count,
        "long_count": total - shorts_count,
        "category_stats": category_stats,
        "channel_top5": channel_top5,
    }
