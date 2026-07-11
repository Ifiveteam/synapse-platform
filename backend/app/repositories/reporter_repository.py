"""Reporter — GlobalTrendsSnapshot·KnowledgeGraph·리포트 조회·저장."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Sequence

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

    ranking_rows = sorted(
        keyword_best.values(),
        key=lambda item: float(item["score"]),
        reverse=True,
    )[:top_keywords_limit]
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


def _iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
