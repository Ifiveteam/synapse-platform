"""Reporter — GlobalTrendsSnapshot·KnowledgeGraph·리포트 조회·저장."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from sqlalchemy import Integer, cast, extract, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.navigator.constants import BEHAVIOR_AXES
from app.models.b2b_trend_report import B2BTrendReport
from app.models.behavior import UserBehaviorLog
from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.models.knowledge_graph import KnowledgeGraph
from app.models.scrap import Scrap
from app.models.trend_domain import TrendDomain
from app.repositories.aggregator_repository import KST, day_window_kst

HEATMAP_DAYS = 7
HEATMAP_DAY_ROWS = 7
HEATMAP_HOUR_COLS = 24
MAX_SIMULATOR_RANGE_DAYS = 90


@dataclass(frozen=True, slots=True)
class SimulationSnapshot:
    """기간 롤업 결과 — KnowledgeGraphMapper 입력용 경량 스냅샷."""

    trending_keywords: dict[str, Any]
    top_domains: dict[str, Any]
    keyword_context_map: dict[str, Any]
    snapshot_count: int
    semantic_links: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class SimulationRollupRow:
    """시뮬레이터 쿼리용 JSONB 슬림 행."""

    snapshot_date: datetime
    trending_keywords: dict[str, Any]
    top_domains: dict[str, Any]
    keyword_context_map: dict[str, Any]
    semantic_links: tuple[dict[str, Any], ...]


async def fetch_snapshot_by_target_date(
    session: AsyncSession,
    target_date: date,
) -> GlobalTrendsSnapshot | None:
    """KST 기준 일자에 해당하는 최신 글로벌 트렌드 스냅샷 1건을 반환한다."""
    window_start, window_end = day_window_kst(target_date)
    result = await session.execute(
        select(GlobalTrendsSnapshot)
        .where(
            GlobalTrendsSnapshot.snapshot_date >= window_start,
            GlobalTrendsSnapshot.snapshot_date < window_end,
        )
        .order_by(GlobalTrendsSnapshot.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def fetch_snapshots_by_date_range(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[GlobalTrendsSnapshot]:
    """KST 일자 구간 내 스냅샷을 일별 최신 1건씩 반환한다 (오름차순)."""
    if end_date < start_date:
        return []

    range_start, _ = day_window_kst(start_date)
    _, range_end = day_window_kst(end_date)
    result = await session.execute(
        select(GlobalTrendsSnapshot)
        .where(
            GlobalTrendsSnapshot.snapshot_date >= range_start,
            GlobalTrendsSnapshot.snapshot_date < range_end,
        )
        .order_by(
            GlobalTrendsSnapshot.snapshot_date.asc(),
            GlobalTrendsSnapshot.created_at.desc(),
        )
    )
    rows = list(result.scalars().all())

    by_day: dict[date, GlobalTrendsSnapshot] = {}
    for row in rows:
        day = row.snapshot_date.astimezone(KST).date()
        if day not in by_day:
            by_day[day] = row

    return [by_day[day] for day in _iter_dates(start_date, end_date) if day in by_day]


async def fetch_simulation_rollup_rows(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[SimulationRollupRow]:
    """시뮬레이터용 JSONB 슬림 컬럼만 인덱스 윈도우로 조회한다."""
    range_start, _ = day_window_kst(start_date)
    _, range_end = day_window_kst(end_date)
    result = await session.execute(
        select(
            GlobalTrendsSnapshot.snapshot_date,
            GlobalTrendsSnapshot.trending_keywords,
            GlobalTrendsSnapshot.top_domains,
            GlobalTrendsSnapshot.keyword_context_map,
            GlobalTrendsSnapshot.semantic_links,
        )
        .where(
            GlobalTrendsSnapshot.snapshot_date >= range_start,
            GlobalTrendsSnapshot.snapshot_date < range_end,
        )
        .order_by(
            GlobalTrendsSnapshot.snapshot_date.asc(),
            GlobalTrendsSnapshot.created_at.desc(),
        )
    )
    rows = result.all()
    by_day: dict[date, SimulationRollupRow] = {}
    for (
        snapshot_date,
        trending_keywords,
        top_domains,
        keyword_context_map,
        semantic_links,
    ) in rows:
        day = snapshot_date.astimezone(KST).date()
        if day in by_day:
            continue
        links_raw = semantic_links if isinstance(semantic_links, list) else []
        by_day[day] = SimulationRollupRow(
            snapshot_date=snapshot_date,
            trending_keywords=trending_keywords
            if isinstance(trending_keywords, dict)
            else {},
            top_domains=top_domains if isinstance(top_domains, dict) else {},
            keyword_context_map=(
                keyword_context_map if isinstance(keyword_context_map, dict) else {}
            ),
            semantic_links=tuple(link for link in links_raw if isinstance(link, dict)),
        )
    return [by_day[day] for day in _iter_dates(start_date, end_date) if day in by_day]


def build_simulation_snapshot(
    rows: Sequence[SimulationRollupRow],
    *,
    top_keywords_limit: int,
    min_score_threshold: float,
) -> SimulationSnapshot | None:
    """기간 내 스냅샷 행을 단일 시뮬레이션 입력으로 롤업한다."""
    if not rows:
        return None

    keyword_best: dict[str, dict[str, Any]] = {}
    merged_contexts: list[dict[str, Any]] = []
    merged_weights: dict[str, dict[str, float]] = {}
    semantic_best: dict[tuple[str, str], dict[str, Any]] = {}
    domain_accum: dict[str, dict[str, float]] = {
        domain.value: {
            "user_count": 0.0,
            "total_duration": 0.0,
            "avg_weight": 0.0,
            "samples": 0.0,
        }
        for domain in TrendDomain
    }

    for row in rows:
        ranking = row.trending_keywords.get("ranking")
        if isinstance(ranking, list):
            for item in ranking:
                if not isinstance(item, dict):
                    continue
                keyword = str(item.get("keyword", "")).strip()
                if not keyword:
                    continue
                score = float(item.get("score", 0.0) or 0.0)
                if score < min_score_threshold:
                    continue
                count_today = int(item.get("count_today", 0) or 0)
                current = keyword_best.get(keyword)
                if current is None:
                    keyword_best[keyword] = {
                        "keyword": keyword,
                        "score": score,
                        "count_today": count_today,
                        "rank": int(item.get("rank", 0) or 0),
                    }
                else:
                    # 주간 롤업: 점수·출현 횟수 누적
                    current["score"] = float(current["score"]) + score
                    current["count_today"] = int(current["count_today"]) + count_today

        keyword_map = row.keyword_context_map or {}
        contexts = keyword_map.get("contexts")
        if isinstance(contexts, list):
            merged_contexts.extend(
                context for context in contexts if isinstance(context, dict)
            )
        weights = keyword_map.get("keyword_domain_weights")
        if isinstance(weights, dict):
            for keyword, domain_weights in weights.items():
                clean_key = str(keyword).strip()
                if not clean_key or not isinstance(domain_weights, dict):
                    continue
                bucket = merged_weights.setdefault(clean_key, {})
                for domain, weight in domain_weights.items():
                    domain_key = str(domain).strip()
                    if not domain_key:
                        continue
                    bucket[domain_key] = bucket.get(domain_key, 0.0) + float(
                        weight or 0.0
                    )

        for link in row.semantic_links:
            left = str(link.get("source", "")).strip()
            right = str(link.get("target", "")).strip()
            if not left or not right or left == right:
                continue
            edge_key = tuple(sorted((left, right)))
            similarity = float(link.get("similarity", 0.0) or 0.0)
            existing = semantic_best.get(edge_key)
            if existing is None or similarity > float(
                existing.get("similarity", 0.0) or 0.0
            ):
                semantic_best[edge_key] = {
                    "source": edge_key[0],
                    "target": edge_key[1],
                    "similarity": similarity,
                    "link_type": "semantic",
                    "left_hint": link.get("left_hint"),
                    "right_hint": link.get("right_hint"),
                    "boosted_cooccurrence": bool(
                        link.get("boosted_cooccurrence", False)
                    ),
                }

        for domain in TrendDomain:
            stats = row.top_domains.get(domain.value)
            if not isinstance(stats, dict):
                continue
            accum = domain_accum[domain.value]
            accum["user_count"] += float(stats.get("user_count", 0) or 0)
            accum["total_duration"] += float(stats.get("total_duration", 0) or 0)
            accum["avg_weight"] += float(stats.get("avg_weight", 0.0) or 0.0)
            accum["samples"] += 1.0

    top_domains: dict[str, Any] = {}
    for domain in TrendDomain:
        accum = domain_accum[domain.value]
        samples = accum["samples"] or 1.0
        top_domains[domain.value] = {
            "user_count": int(accum["user_count"]),
            "total_duration": int(accum["total_duration"]),
            "main_category": domain.value,
            "avg_weight": round(accum["avg_weight"] / samples, 6),
        }

    ranking_rows = _select_domain_balanced_keywords(
        keyword_best,
        merged_weights,
        top_keywords_limit=top_keywords_limit,
    )
    for index, item in enumerate(ranking_rows, start=1):
        item["rank"] = index

    return SimulationSnapshot(
        trending_keywords={"ranking": ranking_rows},
        top_domains=top_domains,
        keyword_context_map={
            "contexts": merged_contexts,
            "keyword_domain_weights": merged_weights,
        },
        snapshot_count=len(rows),
        semantic_links=tuple(semantic_best.values()),
    )


def _select_domain_balanced_keywords(
    keyword_best: dict[str, dict[str, Any]],
    merged_weights: Mapping[str, Mapping[str, float]],
    *,
    top_keywords_limit: int,
) -> list[dict[str, Any]]:
    """도메인별 최소 쿼터를 보장한 뒤 점수 순으로 TopN을 채운다."""
    if not keyword_best or top_keywords_limit <= 0:
        return []

    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for keyword, item in keyword_best.items():
        weights = merged_weights.get(keyword) or {}
        if weights:
            domain = max(weights.items(), key=lambda pair: float(pair[1] or 0.0))[0]
        else:
            domain = TrendDomain.SOCIAL_CURRENT_AFFAIRS.value
        by_domain[str(domain)].append(item)

    for rows in by_domain.values():
        rows.sort(key=lambda row: float(row["score"]), reverse=True)

    domain_list = [domain.value for domain in TrendDomain]
    per_domain = max(1, top_keywords_limit // len(domain_list))
    selected: list[dict[str, Any]] = []
    used: set[str] = set()

    for domain in domain_list:
        for item in by_domain.get(domain, [])[:per_domain]:
            keyword = str(item["keyword"])
            if keyword in used:
                continue
            selected.append(item)
            used.add(keyword)

    leftovers = sorted(
        (item for item in keyword_best.values() if str(item["keyword"]) not in used),
        key=lambda row: float(row["score"]),
        reverse=True,
    )
    for item in leftovers:
        if len(selected) >= top_keywords_limit:
            break
        selected.append(item)
        used.add(str(item["keyword"]))

    selected.sort(key=lambda row: float(row["score"]), reverse=True)
    return selected[:top_keywords_limit]


async def fetch_b2b_report_markdown_by_date(
    session: AsyncSession,
    target_date: date,
) -> str | None:
    """KST 기준 일자에 생성된 B2B 리포트 마크다운 1건을 반환한다."""
    window_start, window_end = day_window_kst(target_date)
    result = await session.execute(
        select(B2BTrendReport.content_markdown)
        .where(
            B2BTrendReport.created_at >= window_start,
            B2BTrendReport.created_at < window_end,
        )
        .order_by(B2BTrendReport.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def fetch_knowledge_graph_by_date(
    session: AsyncSession,
    graph_date: date,
) -> KnowledgeGraph | None:
    """graph_date 기준 지식 그래프 1건을 반환한다."""
    result = await session.execute(
        select(KnowledgeGraph).where(KnowledgeGraph.graph_date == graph_date).limit(1)
    )
    return result.scalar_one_or_none()


async def fetch_activity_heatmap_counts(
    session: AsyncSession,
    *,
    days: int = HEATMAP_DAYS,
    anchor_date: date | None = None,
) -> tuple[list[list[int]], int]:
    """최근 N일 행동·스크랩 빈도를 요일(0=월)~시간(0~23) 매트릭스로 집계한다."""
    end_date = anchor_date or datetime.now(KST).date()
    start_date = end_date - timedelta(days=days - 1)
    window_start, _ = day_window_kst(start_date)
    _, window_end = day_window_kst(end_date)

    matrix = [[0 for _ in range(HEATMAP_HOUR_COLS)] for _ in range(HEATMAP_DAY_ROWS)]
    max_count = 0

    behavior_day = cast(
        extract("isodow", func.timezone("Asia/Seoul", UserBehaviorLog.timestamp)) - 1,
        Integer,
    ).label("day_of_week")
    behavior_hour = cast(
        extract("hour", func.timezone("Asia/Seoul", UserBehaviorLog.timestamp)),
        Integer,
    ).label("hour_of_day")

    behavior_rows = await session.execute(
        select(behavior_day, behavior_hour, func.count())
        .where(
            UserBehaviorLog.timestamp >= window_start,
            UserBehaviorLog.timestamp < window_end,
        )
        .group_by(behavior_day, behavior_hour)
    )

    for day_idx, hour_idx, count in behavior_rows.all():
        if day_idx is None or hour_idx is None:
            continue
        day = int(day_idx)
        hour = int(hour_idx)
        if not (0 <= day < HEATMAP_DAY_ROWS and 0 <= hour < HEATMAP_HOUR_COLS):
            continue
        value = int(count)
        matrix[day][hour] += value
        max_count = max(max_count, matrix[day][hour])

    scrap_day = cast(
        extract("isodow", func.timezone("Asia/Seoul", Scrap.created_at)) - 1,
        Integer,
    ).label("day_of_week")
    scrap_hour = cast(
        extract("hour", func.timezone("Asia/Seoul", Scrap.created_at)),
        Integer,
    ).label("hour_of_day")

    scrap_rows = await session.execute(
        select(scrap_day, scrap_hour, func.count())
        .where(
            Scrap.created_at >= window_start,
            Scrap.created_at < window_end,
        )
        .group_by(scrap_day, scrap_hour)
    )

    for day_idx, hour_idx, count in scrap_rows.all():
        if day_idx is None or hour_idx is None:
            continue
        day = int(day_idx)
        hour = int(hour_idx)
        if not (0 <= day < HEATMAP_DAY_ROWS and 0 <= hour < HEATMAP_HOUR_COLS):
            continue
        value = int(count)
        matrix[day][hour] += value
        max_count = max(max_count, matrix[day][hour])

    return matrix, max_count


def build_stream_series_point(snapshot: GlobalTrendsSnapshot) -> dict[str, Any]:
    """스냅샷 1건을 스트림그래프 시계열 포인트로 변환한다."""
    day = snapshot.snapshot_date.astimezone(KST).date().isoformat()
    axes_raw = snapshot.global_8_axis_avg or {}
    axes = {
        axis: round(float(axes_raw.get(axis, 0.0) or 0.0), 4) for axis in BEHAVIOR_AXES
    }

    domains_raw = snapshot.top_domains or {}
    domains: dict[str, float] = {}
    for domain in TrendDomain:
        bucket = domains_raw.get(domain.value)
        if isinstance(bucket, dict):
            domains[domain.value] = round(
                float(bucket.get("avg_weight", 0.0) or 0.0),
                4,
            )
        else:
            domains[domain.value] = 0.0

    return {
        "date": day,
        "axes": axes,
        "domains": domains,
    }


async def upsert_knowledge_graph(
    session: AsyncSession,
    *,
    graph_date: date,
    snapshot_id: uuid.UUID | None,
    graph_data: dict[str, Any],
    meta: dict[str, Any],
) -> KnowledgeGraph:
    """graph_date 기준 UPSERT — 동일 일자 재생성 시 덮어쓴다."""
    stmt = (
        insert(KnowledgeGraph)
        .values(
            graph_date=graph_date,
            snapshot_id=snapshot_id,
            graph_data=graph_data,
            meta=meta,
        )
        .on_conflict_do_update(
            index_elements=[KnowledgeGraph.graph_date],
            set_={
                "snapshot_id": snapshot_id,
                "graph_data": graph_data,
                "meta": meta,
                "generated_at": func.now(),
            },
        )
        .returning(KnowledgeGraph)
    )
    result = await session.execute(stmt)
    row = result.scalar_one()
    await session.flush()
    return row


@dataclass(frozen=True, slots=True)
class SnapshotInventoryItem:
    """관리자용 일별 스냅샷 존재 여부·요약."""

    date: date
    present: bool
    snapshot_id: str | None = None
    created_at: datetime | None = None
    keyword_count: int = 0
    top_keywords: tuple[str, ...] = ()
    domain_keys: tuple[str, ...] = ()


async def fetch_snapshot_inventory(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[SnapshotInventoryItem]:
    """기간 내 일자별 스냅샷 유무와 키워드·도메인 요약을 반환한다."""
    if end_date < start_date:
        return []

    full_rows = await fetch_snapshots_by_date_range(session, start_date, end_date)
    full_by_day = {row.snapshot_date.astimezone(KST).date(): row for row in full_rows}

    items: list[SnapshotInventoryItem] = []
    for day in _iter_dates(start_date, end_date):
        full = full_by_day.get(day)
        if full is None:
            items.append(SnapshotInventoryItem(date=day, present=False))
            continue

        trending = (
            full.trending_keywords if isinstance(full.trending_keywords, dict) else {}
        )
        ranking = trending.get("ranking")
        keywords: list[str] = []
        if isinstance(ranking, list):
            for entry in ranking:
                if not isinstance(entry, dict):
                    continue
                kw = str(entry.get("keyword", "")).strip()
                if kw:
                    keywords.append(kw)

        top_domains = full.top_domains if isinstance(full.top_domains, dict) else {}
        domain_keys = [
            domain
            for domain, stats in top_domains.items()
            if isinstance(stats, dict) and float(stats.get("avg_weight", 0) or 0) > 0
        ]

        items.append(
            SnapshotInventoryItem(
                date=day,
                present=True,
                snapshot_id=str(full.id),
                created_at=full.created_at,
                keyword_count=len(keywords),
                top_keywords=tuple(keywords[:5]),
                domain_keys=tuple(domain_keys),
            )
        )
    return items


@dataclass(frozen=True, slots=True)
class SnapshotDetail:
    """관리자용 단일 일자 스냅샷 상세."""

    date: date
    present: bool
    snapshot_id: str | None = None
    snapshot_date: datetime | None = None
    created_at: datetime | None = None
    keywords: tuple[dict[str, Any], ...] = ()
    domains: tuple[dict[str, Any], ...] = ()
    axes: dict[str, float] | None = None
    semantic_link_count: int = 0
    semantic_links: tuple[dict[str, Any], ...] = ()
    external_keywords: tuple[str, ...] = ()
    scrap_categories: tuple[str, ...] = ()
    context_count: int = 0
    has_cross_domain_insights: bool = False


async def fetch_snapshot_detail(
    session: AsyncSession,
    target_date: date,
) -> SnapshotDetail:
    """단일 일자 스냅샷을 관리자 상세용으로 반환한다."""
    row = await fetch_snapshot_by_target_date(session, target_date)
    if row is None:
        return SnapshotDetail(date=target_date, present=False)

    trending = row.trending_keywords if isinstance(row.trending_keywords, dict) else {}
    ranking = trending.get("ranking")
    keywords: list[dict[str, Any]] = []
    if isinstance(ranking, list):
        for entry in ranking:
            if not isinstance(entry, dict):
                continue
            kw = str(entry.get("keyword", "")).strip()
            if not kw:
                continue
            keywords.append(
                {
                    "keyword": kw,
                    "score": float(entry.get("score", 0) or 0),
                    "count_today": int(entry.get("count_today", 0) or 0),
                    "rank": int(entry.get("rank", 0) or 0),
                }
            )

    top_domains = row.top_domains if isinstance(row.top_domains, dict) else {}
    domains: list[dict[str, Any]] = []
    for domain, stats in top_domains.items():
        if not isinstance(stats, dict):
            continue
        domains.append(
            {
                "domain": str(domain),
                "user_count": int(stats.get("user_count", 0) or 0),
                "total_duration": int(stats.get("total_duration", 0) or 0),
                "avg_weight": float(stats.get("avg_weight", 0) or 0),
            }
        )
    domains.sort(key=lambda item: item["avg_weight"], reverse=True)

    axes_raw = row.global_8_axis_avg if isinstance(row.global_8_axis_avg, dict) else {}
    axes = {
        str(key): float(value or 0)
        for key, value in axes_raw.items()
        if isinstance(value, (int, float))
    }

    links_raw = row.semantic_links if isinstance(row.semantic_links, list) else []
    links: list[dict[str, Any]] = []
    for link in links_raw:
        if not isinstance(link, dict):
            continue
        source = str(link.get("source", "")).strip()
        target = str(link.get("target", "")).strip()
        if not source or not target:
            continue
        links.append(
            {
                "source": source,
                "target": target,
                "similarity": float(link.get("similarity", 0) or 0),
                "link_type": str(link.get("link_type") or "semantic"),
            }
        )
    links.sort(key=lambda item: item["similarity"], reverse=True)

    external = (
        row.external_market_keywords
        if isinstance(row.external_market_keywords, dict)
        else {}
    )
    external_keywords: list[str] = []
    for key in ("naver", "google", "keywords", "items", "ranking"):
        bucket = external.get(key)
        if isinstance(bucket, list):
            for item in bucket[:10]:
                if isinstance(item, str) and item.strip():
                    external_keywords.append(item.strip())
                elif isinstance(item, dict):
                    label = str(
                        item.get("keyword")
                        or item.get("query")
                        or item.get("name")
                        or ""
                    ).strip()
                    if label:
                        external_keywords.append(label)
    if not external_keywords:
        for value in external.values():
            if isinstance(value, list):
                for item in value[:8]:
                    if isinstance(item, str) and item.strip():
                        external_keywords.append(item.strip())
                    elif isinstance(item, dict):
                        label = str(item.get("keyword") or "").strip()
                        if label:
                            external_keywords.append(label)

    scrap = (
        row.top_scrap_categories if isinstance(row.top_scrap_categories, dict) else {}
    )
    scrap_categories: list[str] = []
    ranking_scrap = (
        scrap.get("ranking") or scrap.get("categories") or scrap.get("items")
    )
    if isinstance(ranking_scrap, list):
        for item in ranking_scrap[:10]:
            if isinstance(item, str) and item.strip():
                scrap_categories.append(item.strip())
            elif isinstance(item, dict):
                label = str(
                    item.get("category")
                    or item.get("name")
                    or item.get("keyword")
                    or ""
                ).strip()
                if label:
                    scrap_categories.append(label)
    elif scrap:
        scrap_categories = [str(key) for key in list(scrap.keys())[:10]]

    context_map = (
        row.keyword_context_map if isinstance(row.keyword_context_map, dict) else {}
    )
    contexts = context_map.get("contexts")
    context_count = len(contexts) if isinstance(contexts, list) else 0

    return SnapshotDetail(
        date=target_date,
        present=True,
        snapshot_id=str(row.id),
        snapshot_date=row.snapshot_date,
        created_at=row.created_at,
        keywords=tuple(keywords),
        domains=tuple(domains),
        axes=axes or None,
        semantic_link_count=len(links),
        semantic_links=tuple(links[:15]),
        external_keywords=tuple(dict.fromkeys(external_keywords)),
        scrap_categories=tuple(dict.fromkeys(scrap_categories)),
        context_count=context_count,
        has_cross_domain_insights=bool(row.cross_domain_insights),
    )


def _iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
