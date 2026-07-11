"""어그리게이터 일별 배치 워커 — Raw 데이터 청크 매핑·플랫폼 집계."""

from __future__ import annotations

import asyncio
import logging
import os
import traceback
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.aggregator.orchestrator import AggregatorOrchestrator
from app.agents.aggregator.schemas import DomainScoreMap
from app.agents.aggregator.semantic import (
    build_semantic_edges,
    collect_keyword_hints,
)
from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger
from app.agents.reporter.graph_mapper import (
    KnowledgeGraphMapper,
    build_keyword_context_map,
)
from app.agents.shared.embedding import EMBEDDING_MODEL, embed_texts
from app.models.trend_domain import TrendDomain
from app.repositories import aggregator_repository as agg_repo
from app.repositories import trend_keyword_embedding_repository as tke_repo
from app.services.external_trend_service import ExternalTrendService
from app.utils.trend_nlp_engine import TrendNLPEngine

_DEFAULT_CHUNK_SIZE = int(os.getenv("AGGREGATOR_CHUNK_SIZE", "100"))

SessionFactory = (
    async_sessionmaker[AsyncSession]
    | Callable[[], AbstractAsyncContextManager[AsyncSession]]
)

_logger = logging.getLogger("app.workers.aggregator")


@dataclass
class _UserDomainSnapshot:
    scores: DomainScoreMap
    observed_at: datetime


@dataclass
class _BatchAccumulator:
    """청크 처리 중 누적되는 플랫폼 집계 상태."""

    user_latest: dict[uuid.UUID, _UserDomainSnapshot] = field(default_factory=dict)
    domain_duration: dict[TrendDomain, int] = field(
        default_factory=lambda: {domain: 0 for domain in TrendDomain}
    )
    scrap_categories: Counter[str] = field(default_factory=Counter)
    keyword_corpus: list[str] = field(default_factory=list)
    # Phase 3-2: 소스·유저 맥락별 동시 출현 키워드 묶음
    keyword_contexts: list[dict[str, Any]] = field(default_factory=list)
    user_daily_keywords: dict[uuid.UUID, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    keyword_domain_totals: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    mapped_row_count: int = 0
    skipped_unmapped_count: int = 0
    error_count: int = 0


class AggregatorWorker:
    """어제 Raw 데이터를 청크 단위로 매핑하고 플랫폼 스냅샷을 생성한다."""

    def __init__(
        self,
        session_factory: SessionFactory,
        orchestrator: AggregatorOrchestrator,
        agg_logger: AggregatorLogger | None = None,
        external_trend_service: ExternalTrendService | None = None,
        nlp_engine: TrendNLPEngine | None = None,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> None:
        self._session_factory = session_factory
        self._orchestrator = orchestrator
        self._agg_logger = agg_logger or AggregatorLogger()
        self._external_trend_service = external_trend_service or ExternalTrendService(
            agg_logger=self._agg_logger
        )
        self._nlp_engine = nlp_engine or TrendNLPEngine()
        self._chunk_size = chunk_size

    async def run_batch(self, target_date: date | None = None) -> None:
        """지정 일자(기본: 어제) 배치를 1회 실행한다."""
        batch_date = target_date or agg_repo.yesterday_kst()
        window_start, window_end = agg_repo.day_window_kst(batch_date)
        snapshot_at = datetime.combine(batch_date, time.min, tzinfo=agg_repo.KST)

        timer_key = self._agg_logger.begin_timer("scrap", "shortcut", "batch")
        _logger.info(
            "[aggregator][batch] 시작 target_date=%s window=[%s, %s)",
            batch_date.isoformat(),
            window_start.isoformat(),
            window_end.isoformat(),
        )

        accumulator = _BatchAccumulator()

        try:
            async with self._open_session() as session:
                try:
                    await self._process_all_chunks(
                        session,
                        window_start,
                        window_end,
                        accumulator,
                    )

                    profiles = await agg_repo.fetch_latest_profile_per_user(session)
                    global_8_axis_avg = agg_repo.compute_global_8_axis_average(profiles)

                    top_domains = self._build_top_domains(accumulator)
                    top_scrap_categories = self._build_scrap_categories(accumulator)
                    has_internal = accumulator.mapped_row_count > 0
                    # 내부 매핑이 없으면 외부 키워드를 trending/공출현에 넣지 않는다.
                    # (빈 일자 스냅샷이 Google RSS만으로 주간 그래프를 오염시키는 것 방지)
                    if has_internal:
                        external_market_keywords = (
                            await self._fetch_external_market_keywords(batch_date)
                        )
                        self._append_external_keywords(
                            accumulator, external_market_keywords
                        )
                    else:
                        external_market_keywords = {}
                        _logger.info(
                            "[aggregator][batch] 내부 매핑 0건 — "
                            "외부 수집·trending 병합 스킵"
                        )

                    trending_keywords = await agg_repo.build_trending_keywords_payload(
                        session,
                        target_date=batch_date,
                        refined_keywords=accumulator.keyword_corpus,
                        nlp_engine=self._nlp_engine,
                    )
                    keyword_context_map = self._build_keyword_context_map(
                        batch_date,
                        accumulator,
                        external_market_keywords,
                    )
                    semantic_links = await self._build_semantic_links(
                        session,
                        trending_keywords=trending_keywords,
                        keyword_context_map=keyword_context_map,
                        external_market_keywords=external_market_keywords,
                    )

                    await agg_repo.insert_global_trends_snapshot(
                        session,
                        snapshot_date=snapshot_at,
                        top_domains=top_domains,
                        top_scrap_categories=top_scrap_categories,
                        external_market_keywords=external_market_keywords,
                        global_8_axis_avg=global_8_axis_avg,
                        trending_keywords=trending_keywords,
                        keyword_context_map=keyword_context_map,
                        semantic_links=semantic_links,
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        except Exception as exc:
            latency_ms = self._agg_logger.end_timer(timer_key)
            _logger.exception(
                "[aggregator][batch] 실패 latency_ms=%.2f error=%s\n%s",
                latency_ms,
                exc,
                traceback.format_exc(),
            )
            raise

        # Phase 3-2: 집계 직후 Reporter 파이프라인(지식 그래프 + 리포트) 비동기 트리거
        try:
            await self._run_reporter_pipeline(batch_date)
        except Exception:
            _logger.exception(
                "[aggregator][batch] Reporter 파이프라인 실패 target_date=%s",
                batch_date.isoformat(),
            )

        latency_ms = self._agg_logger.end_timer(timer_key)
        _logger.info(
            "[aggregator][batch] 완료 latency_ms=%.2f "
            "mapped=%d skipped_unmapped=%d errors=%d users=%d "
            "trending_keywords=%d",
            latency_ms,
            accumulator.mapped_row_count,
            accumulator.skipped_unmapped_count,
            accumulator.error_count,
            len(accumulator.user_latest),
            len(accumulator.keyword_corpus),
        )

    def _open_session(self) -> AbstractAsyncContextManager[AsyncSession]:
        return self._session_factory()

    async def _build_semantic_links(
        self,
        session: AsyncSession,
        *,
        trending_keywords: dict[str, Any],
        keyword_context_map: dict[str, Any],
        external_market_keywords: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """힌트 결합 임베딩 → Top-K semantic edges.

        임베딩·유사도 연산은 이벤트 루프 블로킹 방지를 위해 to_thread.
        실패 시 [] 로 degrade (스냅샷·공출현 그래프는 유지).
        """
        try:
            hints = collect_keyword_hints(
                trending_keywords=trending_keywords,
                keyword_context_map=keyword_context_map,
                external_market_keywords=external_market_keywords,
            )
            if len(hints) < 2:
                _logger.info(
                    "[aggregator][semantic] 후보 부족 hints=%d — skip",
                    len(hints),
                )
                return []

            texts = [hint.embedding_text for hint in hints]
            cached = await tke_repo.fetch_by_embedding_texts(session, texts)
            missing = [hint for hint in hints if hint.embedding_text not in cached]

            if missing:
                miss_texts = [hint.embedding_text for hint in missing]
                vectors = await asyncio.to_thread(embed_texts, miss_texts)
                await tke_repo.upsert_many(
                    session,
                    [
                        {
                            "keyword": hint.keyword,
                            "hint_source": hint.hint_source,
                            "hint_domain": hint.hint_domain,
                            "embedding_text": hint.embedding_text,
                            "embedding": vector,
                            "model": EMBEDDING_MODEL,
                        }
                        for hint, vector in zip(missing, vectors, strict=True)
                    ],
                )
                for hint, vector in zip(missing, vectors, strict=True):
                    cached[hint.embedding_text] = vector

            keyword_set = {hint.keyword for hint in hints}
            co_matrix = KnowledgeGraphMapper._build_cooccurrence_matrix(
                {
                    "target_date": str(keyword_context_map.get("target_date", "")),
                    "contexts": list(keyword_context_map.get("contexts") or []),
                    "keyword_domain_weights": dict(
                        keyword_context_map.get("keyword_domain_weights") or {}
                    ),
                },
                keyword_set=keyword_set,
            )

            edges = await asyncio.to_thread(
                build_semantic_edges,
                hints=hints,
                vectors=cached,
                co_matrix=co_matrix,
            )
            payload = [edge.to_json() for edge in edges]
            _logger.info(
                "[aggregator][semantic] 완료 hints=%d cache_hit=%d "
                "embedded=%d edges=%d",
                len(hints),
                len(hints) - len(missing),
                len(missing),
                len(payload),
            )
            return payload
        except Exception:
            _logger.exception(
                "[aggregator][semantic] 실패 — semantic_links=[] 로 degrade"
            )
            return []

    async def _fetch_external_market_keywords(self, batch_date: date) -> dict[str, Any]:
        """외부 트렌드 수집 — 장애 시 {} 반환하여 내부 집계만 저장."""
        timer_key = self._agg_logger.begin_timer("behavior", "llm", "external_trends")
        try:
            result = await self._external_trend_service.collect_market_keywords_safe(
                target_date=batch_date,
            )
            latency_ms = self._agg_logger.end_timer(timer_key)
            _logger.info(
                "[aggregator][batch][external] 수집 완료 latency_ms=%.2f "
                "domains=%d status=%s",
                latency_ms,
                len(result.get("by_domain", {})) if result else 0,
                result.get("collection_status") if result else "empty",
            )
            return result
        except Exception as exc:
            latency_ms = self._agg_logger.end_timer(timer_key)
            self._agg_logger.log_failure(
                "behavior",
                "llm",
                operation="external_trends",
                latency_ms=latency_ms,
                error=exc,
            )
            _logger.exception(
                "[aggregator][batch][external] 수집 치명적 오류 — "
                "내부 집계만 저장 latency_ms=%.2f",
                latency_ms,
            )
            return {}

    async def _process_all_chunks(
        self,
        session: AsyncSession,
        window_start: datetime,
        window_end: datetime,
        accumulator: _BatchAccumulator,
    ) -> None:
        await self._process_scrap_chunks(session, window_start, window_end, accumulator)
        await self._process_youtube_chunks(
            session, window_start, window_end, accumulator
        )
        await self._process_behavior_chunks(
            session, window_start, window_end, accumulator
        )

    async def _process_scrap_chunks(
        self,
        session: AsyncSession,
        window_start: datetime,
        window_end: datetime,
        accumulator: _BatchAccumulator,
    ) -> None:
        offset = 0
        chunk_index = 0
        while True:
            rows = await agg_repo.fetch_scraps_chunk(
                session,
                window_start,
                window_end,
                offset=offset,
                limit=self._chunk_size,
            )
            if not rows:
                break

            chunk_index += 1
            await self._map_scrap_chunk(rows, accumulator)
            _logger.info(
                "[aggregator][batch][scrap] 청크 %d 완료 rows=%d offset=%d",
                chunk_index,
                len(rows),
                offset,
            )
            offset += len(rows)
            if len(rows) < self._chunk_size:
                break

    async def _process_youtube_chunks(
        self,
        session: AsyncSession,
        window_start: datetime,
        window_end: datetime,
        accumulator: _BatchAccumulator,
    ) -> None:
        offset = 0
        chunk_index = 0
        while True:
            rows = await agg_repo.fetch_watch_catalog_chunk(
                session,
                window_start,
                window_end,
                offset=offset,
                limit=self._chunk_size,
            )
            if not rows:
                break

            chunk_index += 1
            await self._map_youtube_chunk(rows, accumulator)
            _logger.info(
                "[aggregator][batch][youtube] 청크 %d 완료 rows=%d offset=%d",
                chunk_index,
                len(rows),
                offset,
            )
            offset += len(rows)
            if len(rows) < self._chunk_size:
                break

    async def _process_behavior_chunks(
        self,
        session: AsyncSession,
        window_start: datetime,
        window_end: datetime,
        accumulator: _BatchAccumulator,
    ) -> None:
        offset = 0
        chunk_index = 0
        while True:
            rows = await agg_repo.fetch_behavior_logs_chunk(
                session,
                window_start,
                window_end,
                offset=offset,
                limit=self._chunk_size,
            )
            if not rows:
                break

            chunk_index += 1
            await self._map_behavior_chunk(rows, accumulator)
            _logger.info(
                "[aggregator][batch][behavior] 청크 %d 완료 rows=%d offset=%d",
                chunk_index,
                len(rows),
                offset,
            )
            offset += len(rows)
            if len(rows) < self._chunk_size:
                break

    async def _map_scrap_chunk(
        self,
        rows: list[Any],
        accumulator: _BatchAccumulator,
    ) -> None:
        for row in rows:
            try:
                mapping = await self._orchestrator.map_scrap_row(row)
                self._ingest_mapped_row(
                    accumulator,
                    user_id=row.user_id,
                    scores=mapping.scores,
                    observed_at=row.created_at,
                    scrap_category=getattr(row, "category", None),
                    trend_keywords=mapping.trend_keywords,
                    source="scrap",
                )
            except Exception:
                accumulator.error_count += 1
                _logger.exception(
                    "[aggregator][batch][scrap] 행 매핑 실패 scrap_id=%s",
                    getattr(row, "id", None),
                )

    async def _map_youtube_chunk(
        self,
        rows: list[Any],
        accumulator: _BatchAccumulator,
    ) -> None:
        for row in rows:
            analysis = getattr(row, "analysis", None)
            try:
                mapping = await self._orchestrator.map_youtube_row(row, analysis)
                self._ingest_mapped_row(
                    accumulator,
                    user_id=row.user_id,
                    scores=mapping.scores,
                    observed_at=row.watched_at,
                    trend_keywords=mapping.trend_keywords,
                    source="youtube",
                )
            except Exception:
                accumulator.error_count += 1
                _logger.exception(
                    "[aggregator][batch][youtube] 행 매핑 실패 catalog_id=%s",
                    getattr(row, "id", None),
                )

    async def _map_behavior_chunk(
        self,
        rows: list[Any],
        accumulator: _BatchAccumulator,
    ) -> None:
        for row in rows:
            try:
                mapping = await self._orchestrator.map_behavior_row(row)
                duration = int(getattr(row, "duration_seconds", 0) or 0)
                self._ingest_mapped_row(
                    accumulator,
                    user_id=row.user_id,
                    scores=mapping.scores,
                    observed_at=row.timestamp,
                    duration_seconds=duration,
                    trend_keywords=mapping.trend_keywords,
                    source="behavior",
                )
            except Exception:
                accumulator.error_count += 1
                _logger.exception(
                    "[aggregator][batch][behavior] 행 매핑 실패 log_id=%s",
                    getattr(row, "id", None),
                )

    @staticmethod
    def _append_keywords(
        accumulator: _BatchAccumulator,
        keywords: list[str] | None,
    ) -> None:
        """에이전트가 정제한 키워드를 코퍼스에 병합."""
        if not keywords:
            return
        accumulator.keyword_corpus.extend(keywords)

    @staticmethod
    def _append_external_keywords(
        accumulator: _BatchAccumulator,
        external_payload: dict[str, Any],
    ) -> None:
        """외부 API(네이버·구글 RSS) 키워드를 코퍼스에 병합."""
        if not external_payload:
            return

        raw = external_payload.get("raw")
        if isinstance(raw, dict):
            for item in raw.get("naver_datalab", []):
                if isinstance(item, dict):
                    AggregatorWorker._split_and_append_keywords(
                        accumulator,
                        item.get("keywords"),
                        item.get("group_name"),
                    )
            for item in raw.get("google_trends", []):
                if isinstance(item, dict) and item.get("keyword"):
                    AggregatorWorker._append_keywords(
                        accumulator,
                        [str(item["keyword"])],
                    )

        by_domain = external_payload.get("by_domain")
        if isinstance(by_domain, dict):
            for bucket in by_domain.values():
                if not isinstance(bucket, dict):
                    continue
                for entry in bucket.get("google", []):
                    if isinstance(entry, dict) and entry.get("keyword"):
                        AggregatorWorker._append_keywords(
                            accumulator,
                            [str(entry["keyword"])],
                        )
                for entry in bucket.get("naver", []):
                    if isinstance(entry, dict):
                        AggregatorWorker._split_and_append_keywords(
                            accumulator,
                            entry.get("keywords"),
                            entry.get("group_name"),
                        )

    @staticmethod
    def _split_and_append_keywords(
        accumulator: _BatchAccumulator,
        *values: str | None,
    ) -> None:
        """쉼표·슬래시 구분 문자열을 개별 키워드로 분리해 추가."""
        for value in values:
            if not value or not str(value).strip():
                continue
            parts = [
                piece.strip()
                for piece in str(value).replace("/", ",").split(",")
                if piece.strip()
            ]
            AggregatorWorker._append_keywords(accumulator, parts)

    def _ingest_mapped_row(
        self,
        accumulator: _BatchAccumulator,
        *,
        user_id: uuid.UUID,
        scores: DomainScoreMap,
        observed_at: datetime,
        scrap_category: str | None = None,
        duration_seconds: int = 0,
        trend_keywords: list[str] | None = None,
        source: str = "scrap",
    ) -> None:
        if self._orchestrator.is_unmapped(scores):
            accumulator.skipped_unmapped_count += 1
            return

        accumulator.mapped_row_count += 1
        self._update_user_latest(accumulator, user_id, scores, observed_at)
        self._append_keywords(accumulator, trend_keywords)
        self._record_keyword_context(
            accumulator,
            source=source,
            trend_keywords=trend_keywords,
            scores=scores,
            user_id=user_id,
        )

        if scrap_category:
            accumulator.scrap_categories[scrap_category.strip()] += 1

        if duration_seconds > 0:
            for domain, weight in scores.items():
                accumulator.domain_duration[domain] += int(duration_seconds * weight)

    @staticmethod
    def _record_keyword_context(
        accumulator: _BatchAccumulator,
        *,
        source: str,
        trend_keywords: list[str] | None,
        scores: DomainScoreMap,
        user_id: uuid.UUID,
    ) -> None:
        """행 단위 키워드 맥락·도메인 가중치·유저 일별 묶음을 누적한다."""
        cleaned = [kw.strip() for kw in (trend_keywords or []) if kw and kw.strip()]
        if not cleaned:
            return

        active_domains = [
            domain.value for domain, weight in scores.items() if float(weight) > 0.0
        ]
        if len(cleaned) >= 2:
            accumulator.keyword_contexts.append(
                {
                    "source": source,
                    "keywords": cleaned,
                    "domains": active_domains,
                }
            )

        for keyword in cleaned:
            accumulator.user_daily_keywords[user_id].add(keyword)
            for domain, weight in scores.items():
                accumulator.keyword_domain_totals[keyword][domain.value] += float(
                    weight
                )

    @classmethod
    def _build_keyword_context_map(
        cls,
        batch_date: date,
        accumulator: _BatchAccumulator,
        external_market_keywords: dict[str, Any],
    ) -> dict[str, Any]:
        """배치 종료 시 keyword_context_map JSONB 페이로드를 조립한다."""
        contexts = list(accumulator.keyword_contexts)

        # 동일 유저의 스크랩·행동·유튜브 키워드 교차 출현 맥락
        for keywords in accumulator.user_daily_keywords.values():
            if len(keywords) >= 2:
                contexts.append(
                    {
                        "source": "user_daily",
                        "keywords": sorted(keywords),
                        "domains": [],
                    }
                )

        contexts.extend(cls._build_external_keyword_contexts(external_market_keywords))

        weights = {
            keyword: dict(domain_map)
            for keyword, domain_map in accumulator.keyword_domain_totals.items()
        }
        return build_keyword_context_map(
            target_date=batch_date.isoformat(),
            contexts=contexts,
            keyword_domain_weights=weights,
        )

    @staticmethod
    def _build_external_keyword_contexts(
        external_payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """외부 시장(구글·네이버) 도메인별 키워드 공존 맥락을 생성한다."""
        if not external_payload:
            return []

        by_domain = external_payload.get("by_domain")
        if not isinstance(by_domain, dict):
            return []

        contexts: list[dict[str, Any]] = []
        for domain_key, bucket in by_domain.items():
            if not isinstance(bucket, dict):
                continue
            keywords: set[str] = set()
            for entry in bucket.get("google", []):
                if isinstance(entry, dict) and entry.get("keyword"):
                    keywords.add(str(entry["keyword"]).strip())
            for entry in bucket.get("naver", []):
                if not isinstance(entry, dict):
                    continue
                group = str(entry.get("group_name", "")).strip()
                if group:
                    keywords.add(group)
                    continue
                raw = str(entry.get("keywords", "")).strip()
                if raw:
                    first = raw.replace("/", ",").split(",")[0].strip()
                    if first:
                        keywords.add(first)
            if len(keywords) >= 2:
                contexts.append(
                    {
                        "source": "external",
                        "keywords": sorted(keywords),
                        "domains": [str(domain_key)],
                    }
                )
        return contexts

    async def _run_reporter_pipeline(self, batch_date: date) -> None:
        """Reporter 일별 파이프라인 — 지식 그래프 UPSERT + 마크다운 리포트 병렬 실행."""
        from app.services.trend_report_service import TrendReportService

        async with self._open_session() as session:
            service = TrendReportService(session)
            await service.run_daily_pipeline(batch_date)
            await session.commit()

    @staticmethod
    def _update_user_latest(
        accumulator: _BatchAccumulator,
        user_id: uuid.UUID,
        scores: DomainScoreMap,
        observed_at: datetime,
    ) -> None:
        existing = accumulator.user_latest.get(user_id)
        if existing is None or observed_at > existing.observed_at:
            accumulator.user_latest[user_id] = _UserDomainSnapshot(
                scores=scores,
                observed_at=observed_at,
            )

    @staticmethod
    def compute_platform_domain_average(
        user_latest: dict[uuid.UUID, _UserDomainSnapshot],
    ) -> dict[TrendDomain, float]:
        """유저별 최신 domain_distribution 평균 — UNMAPPED 유저는 분모에서 제외."""
        if not user_latest:
            return {domain: 0.0 for domain in TrendDomain}

        totals = {domain: 0.0 for domain in TrendDomain}
        user_count = len(user_latest)

        for snapshot in user_latest.values():
            for domain in TrendDomain:
                totals[domain] += snapshot.scores.get(domain, 0.0)

        return {domain: round(totals[domain] / user_count, 6) for domain in TrendDomain}

    def _build_top_domains(self, accumulator: _BatchAccumulator) -> dict:
        top_domains = agg_repo.empty_top_domains_template()
        platform_avg = self.compute_platform_domain_average(accumulator.user_latest)

        for domain in TrendDomain:
            users_with_domain = {
                user_id
                for user_id, snapshot in accumulator.user_latest.items()
                if snapshot.scores.get(domain, 0.0) > 0.0
            }
            key = domain.value
            top_domains[key]["user_count"] = len(users_with_domain)
            top_domains[key]["total_duration"] = accumulator.domain_duration[domain]
            top_domains[key]["avg_weight"] = platform_avg[domain]

        return top_domains

    @staticmethod
    def _build_scrap_categories(accumulator: _BatchAccumulator) -> dict:
        if not accumulator.scrap_categories:
            return {}
        ranked = accumulator.scrap_categories.most_common(20)
        return {
            category: {"count": count, "rank": index}
            for index, (category, count) in enumerate(ranked, start=1)
        }


async def run_aggregation_pipeline(
    session_factory: SessionFactory | None = None,
    orchestrator: AggregatorOrchestrator | None = None,
    *,
    target_date: date | None = None,
) -> None:
    """스케줄러·수동 트리거용 편의 진입점."""
    from app.core.database.session import AsyncSessionLocal

    factory = session_factory or AsyncSessionLocal
    worker = AggregatorWorker(
        session_factory=factory,
        orchestrator=orchestrator or AggregatorOrchestrator(),
    )
    await worker.run_batch(target_date=target_date)
