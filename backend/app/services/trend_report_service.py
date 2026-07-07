"""B2B 트렌드 마크다운 리포트·지식 그래프 생성 서비스 — Reporter 에이전트 연동."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.reporter.compressor import CompressedSnapshot, DataCompressor
from app.agents.reporter.constants import (
    MIN_DOMAIN_ACTIVE_USERS,
    MIN_TRENDING_KEYWORDS,
    REPORTER_GEMINI_MODEL,
    REPORTER_MAX_OUTPUT_TOKENS,
    REPORTER_TEMPERATURE,
)
from app.agents.reporter.graph_mapper import AgentKeywordMap, KnowledgeGraphMapper
from app.agents.reporter.prompts import (
    MASTER_REPORT_SYSTEM_PROMPT,
    build_report_user_prompt,
)
from app.agents.shared.gemini import get_client
from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.repositories import reporter_repository
from app.utils.notifier import NewsletterDispatchResult, TrendNewsletterDispatcher
from app.utils.report_filer import (
    DEFAULT_REPORT_RETENTION_DAYS,
    REPORT_RETENTION_DAYS_ENV,
    PurgeResult,
    ReportFiler,
)

logger = logging.getLogger(__name__)

_UNAVAILABLE_REPORT_TEMPLATE = """\
# 시냅스 트렌드 인텔리전스 리포트

**분석 기준일:** {target_date}

---

해당 일자의 플랫폼 집계 데이터가 아직 준비되지 않았거나, 리포트 생성에 필요한 최소 통계량을 충족하지 못했습니다.

- 일별 어그리게이터 배치 완료 후 다시 시도해 주세요.
- 문의: Synapse Intelligence Team
"""

_GENERATION_ERROR_TEMPLATE = """\
# 시냅스 트렌드 인텔리전스 리포트

**분석 기준일:** {target_date}

---

리포트 생성 중 일시적 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.

- 오류 코드: `{error_code}`
"""


@dataclass(frozen=True, slots=True)
class TrendReportResult:
    """리포트 생성·파일링 결과."""

    markdown: str
    target_date: date
    generated: bool
    snapshot_id: uuid.UUID | None = None
    compression_ratio: float | None = None
    reason: str | None = None
    file_path: str | None = None
    file_size_bytes: int | None = None
    file_persisted: bool = False


@dataclass(frozen=True, slots=True)
class KnowledgeGraphResult:
    """지식 그래프 생성·저장 결과."""

    target_date: date
    generated: bool
    graph_data: dict[str, Any] | None = None
    snapshot_id: uuid.UUID | None = None
    knowledge_graph_id: uuid.UUID | None = None
    meta: dict[str, Any] | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReporterPipelineResult:
    """일별 Reporter 파이프라인(그래프 + 리포트 + 파일링) 통합 결과."""

    target_date: date
    graph: KnowledgeGraphResult
    report: TrendReportResult
    purge: PurgeResult | None = None
    newsletter: NewsletterDispatchResult | None = None


class TrendReportService:
    """GlobalTrendsSnapshot → 지식 그래프 + 압축 → Gemini → 마크다운 리포트 → 정적 파일."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        graph_mapper: KnowledgeGraphMapper | None = None,
        report_filer: ReportFiler | None = None,
    ) -> None:
        self._session = session
        self._graph_mapper = graph_mapper or KnowledgeGraphMapper()
        self._report_filer = report_filer or ReportFiler()

    async def run_daily_pipeline(self, target_date: date) -> ReporterPipelineResult:
        """지식 그래프 UPSERT, 마크다운 리포트 생성, 파일 저장, 만료 청소를 실행한다."""
        snapshot = await reporter_repository.fetch_snapshot_by_target_date(
            self._session,
            target_date,
        )
        if snapshot is None:
            logger.warning(
                "[reporter][pipeline] 스냅샷 없음 target_date=%s",
                target_date.isoformat(),
            )
            empty_graph = KnowledgeGraphResult(
                target_date=target_date,
                generated=False,
                reason="snapshot_not_found",
            )
            empty_report = TrendReportResult(
                markdown=_UNAVAILABLE_REPORT_TEMPLATE.format(
                    target_date=target_date.isoformat(),
                ),
                target_date=target_date,
                generated=False,
                reason="snapshot_not_found",
            )
            purge = await self._run_retention_cleaner()
            return ReporterPipelineResult(
                target_date=target_date,
                graph=empty_graph,
                report=empty_report,
                purge=purge,
            )

        graph_result, report_result = await asyncio.gather(
            self.build_and_persist_knowledge_graph(
                target_date,
                snapshot=snapshot,
            ),
            self.generate_markdown_report(target_date, snapshot=snapshot),
        )

        # Phase 3-3: 성공 생성 리포트만 물리 .md 파일로 영구 저장
        filed_report = await self._persist_report_to_storage(report_result)

        # Phase 4-4: 물리 파일링 성공 시 B2B 뉴스레터 백그라운드 발송
        newsletter = await self._dispatch_newsletter_push(filed_report)

        # 파이프라인 마감 직전 만료 파일·빈 디렉토리 청소
        purge = await self._run_retention_cleaner()

        return ReporterPipelineResult(
            target_date=target_date,
            graph=graph_result,
            report=filed_report,
            purge=purge,
            newsletter=newsletter,
        )

    async def _persist_report_to_storage(
        self,
        report: TrendReportResult,
    ) -> TrendReportResult:
        """Gemini 생성 리포트를 ReportFiler로 디스크에 저장한다."""
        if not report.generated:
            logger.info(
                "[reporter][file] 생성 실패 리포트 — 파일 저장 skip date=%s reason=%s",
                report.target_date.isoformat(),
                report.reason,
            )
            return report

        try:
            file_result = await self._report_filer.save_report(
                report.target_date,
                report.markdown,
            )
        except (PermissionError, OSError):
            logger.exception(
                "[reporter][file] 저장 실패 date=%s",
                report.target_date.isoformat(),
            )
            return TrendReportResult(
                markdown=report.markdown,
                target_date=report.target_date,
                generated=report.generated,
                snapshot_id=report.snapshot_id,
                compression_ratio=report.compression_ratio,
                reason="file_persist_error",
                file_persisted=False,
            )

        absolute_path = str(file_result.file_path.resolve())
        logger.info(
            "[reporter][file] 물리 저장 완료 path=%s size=%d bytes written=%s",
            absolute_path,
            file_result.size_bytes,
            file_result.written,
        )
        return TrendReportResult(
            markdown=report.markdown,
            target_date=report.target_date,
            generated=report.generated,
            snapshot_id=report.snapshot_id,
            compression_ratio=report.compression_ratio,
            file_path=absolute_path,
            file_size_bytes=file_result.size_bytes,
            file_persisted=True,
        )

    async def _run_retention_cleaner(self) -> PurgeResult | None:
        """REPORT_RETENTION_DAYS 기준 만료 리포트를 청소한다."""
        retention_days = int(
            os.getenv(REPORT_RETENTION_DAYS_ENV, DEFAULT_REPORT_RETENTION_DAYS)
        )
        try:
            return await self._report_filer.purge_expired_reports(retention_days)
        except (PermissionError, OSError, ValueError):
            logger.exception(
                "[reporter][purge] 생명주기 청소 실패 retention_days=%d",
                retention_days,
            )
            return None

    async def _dispatch_newsletter_push(
        self,
        report: TrendReportResult,
    ) -> NewsletterDispatchResult:
        """파일 저장에 성공한 리포트를 B2B 구독자에게 백그라운드 발송한다."""
        if not report.generated or not report.file_persisted:
            logger.info(
                "[reporter][newsletter] 발송 skip date=%s generated=%s persisted=%s",
                report.target_date.isoformat(),
                report.generated,
                report.file_persisted,
            )
            return NewsletterDispatchResult(
                attempted=False,
                sent_count=0,
                failed_count=0,
                skipped_reason="report_not_persisted",
            )

        dispatcher = TrendNewsletterDispatcher(self._report_filer)

        def _log_task_result(task: asyncio.Task[NewsletterDispatchResult]) -> None:
            try:
                result = task.result()
                logger.info(
                    "[reporter][newsletter] 백그라운드 완료 date=%s sent=%d failed=%d",
                    report.target_date.isoformat(),
                    result.sent_count,
                    result.failed_count,
                )
            except Exception:
                logger.exception(
                    "[reporter][newsletter] 백그라운드 태스크 실패 date=%s",
                    report.target_date.isoformat(),
                )

        try:
            task = asyncio.create_task(
                dispatcher.dispatch_daily_newsletter(report.target_date),
                name=f"newsletter-{report.target_date.isoformat()}",
            )
            task.add_done_callback(_log_task_result)
            return NewsletterDispatchResult(
                attempted=True,
                sent_count=0,
                failed_count=0,
                subscriber_count=len(dispatcher.resolve_subscribers()),
                skipped_reason="background_scheduled",
            )
        except Exception:
            logger.exception(
                "[reporter][newsletter] 스케줄 실패 date=%s",
                report.target_date.isoformat(),
            )
            return NewsletterDispatchResult(
                attempted=False,
                sent_count=0,
                failed_count=0,
                skipped_reason="schedule_error",
            )

    async def build_and_persist_knowledge_graph(
        self,
        target_date: date,
        *,
        snapshot: GlobalTrendsSnapshot | None = None,
        keyword_map: AgentKeywordMap | None = None,
    ) -> KnowledgeGraphResult:
        """KnowledgeGraphMapper로 그래프를 생성하고 knowledge_graphs에 UPSERT한다."""
        row = snapshot or await reporter_repository.fetch_snapshot_by_target_date(
            self._session,
            target_date,
        )
        if row is None:
            logger.warning(
                "[reporter][graph] 스냅샷 없음 target_date=%s",
                target_date.isoformat(),
            )
            return KnowledgeGraphResult(
                target_date=target_date,
                generated=False,
                reason="snapshot_not_found",
            )

        if not self._is_graph_data_sufficient(row):
            logger.warning(
                "[reporter][graph] 데이터 부족 target_date=%s snapshot_id=%s",
                target_date.isoformat(),
                row.id,
            )
            return KnowledgeGraphResult(
                target_date=target_date,
                generated=False,
                snapshot_id=row.id,
                reason="insufficient_data",
            )

        try:
            graph_data, meta = self._graph_mapper.map_with_meta(row, keyword_map)
            saved = await reporter_repository.upsert_knowledge_graph(
                self._session,
                graph_date=target_date,
                snapshot_id=row.id,
                graph_data=graph_data,
                meta=meta,
            )
        except Exception:
            logger.exception(
                "[reporter][graph] 생성·저장 실패 target_date=%s snapshot_id=%s",
                target_date.isoformat(),
                row.id,
            )
            return KnowledgeGraphResult(
                target_date=target_date,
                generated=False,
                snapshot_id=row.id,
                reason="graph_persist_error",
            )

        logger.info(
            "[reporter][graph] UPSERT 완료 target_date=%s nodes=%d links=%d id=%s",
            target_date.isoformat(),
            meta.get("node_count", 0),
            meta.get("link_count", 0),
            saved.id,
        )
        return KnowledgeGraphResult(
            target_date=target_date,
            generated=True,
            graph_data=graph_data,
            snapshot_id=row.id,
            knowledge_graph_id=saved.id,
            meta=meta,
        )

    async def generate_markdown_report(
        self,
        target_date: date,
        *,
        snapshot: GlobalTrendsSnapshot | None = None,
    ) -> TrendReportResult:
        """target_date 기준 B2B 마크다운 리포트를 생성한다."""
        row = snapshot or await reporter_repository.fetch_snapshot_by_target_date(
            self._session,
            target_date,
        )
        if row is None:
            logger.warning(
                "[reporter] 스냅샷 없음 target_date=%s",
                target_date.isoformat(),
            )
            return TrendReportResult(
                markdown=_UNAVAILABLE_REPORT_TEMPLATE.format(
                    target_date=target_date.isoformat(),
                ),
                target_date=target_date,
                generated=False,
                reason="snapshot_not_found",
            )

        if not self._is_data_sufficient(row):
            logger.warning(
                "[reporter] 데이터 부족 target_date=%s snapshot_id=%s",
                target_date.isoformat(),
                row.id,
            )
            return TrendReportResult(
                markdown=_UNAVAILABLE_REPORT_TEMPLATE.format(
                    target_date=target_date.isoformat(),
                ),
                target_date=target_date,
                generated=False,
                snapshot_id=row.id,
                reason="insufficient_data",
            )

        compressed = DataCompressor.compress_snapshot(row)
        logger.info(
            "[reporter] 데이터 압축 완료 target_date=%s raw=%d compact=%d ratio=%.2f%%",
            target_date.isoformat(),
            compressed.raw_json_chars,
            compressed.compressed_chars,
            compressed.compression_ratio * 100,
        )

        try:
            markdown = await self._invoke_gemini_report(compressed)
        except Exception:
            logger.exception(
                "[reporter] Gemini 리포트 생성 실패 target_date=%s snapshot_id=%s",
                target_date.isoformat(),
                row.id,
            )
            return TrendReportResult(
                markdown=_GENERATION_ERROR_TEMPLATE.format(
                    target_date=target_date.isoformat(),
                    error_code="gemini_generation_failed",
                ),
                target_date=target_date,
                generated=False,
                snapshot_id=row.id,
                compression_ratio=compressed.compression_ratio,
                reason="gemini_error",
            )

        if not markdown.strip():
            logger.error(
                "[reporter] Gemini 빈 응답 target_date=%s snapshot_id=%s",
                target_date.isoformat(),
                row.id,
            )
            return TrendReportResult(
                markdown=_GENERATION_ERROR_TEMPLATE.format(
                    target_date=target_date.isoformat(),
                    error_code="empty_llm_response",
                ),
                target_date=target_date,
                generated=False,
                snapshot_id=row.id,
                compression_ratio=compressed.compression_ratio,
                reason="empty_response",
            )

        logger.info(
            "[reporter] 리포트 생성 완료 target_date=%s snapshot_id=%s chars=%d",
            target_date.isoformat(),
            row.id,
            len(markdown),
        )
        return TrendReportResult(
            markdown=markdown.strip(),
            target_date=target_date,
            generated=True,
            snapshot_id=row.id,
            compression_ratio=compressed.compression_ratio,
        )

    @staticmethod
    def _is_data_sufficient(snapshot: GlobalTrendsSnapshot) -> bool:
        """마크다운 리포트 생성 최소 데이터 여부."""
        trending = snapshot.trending_keywords or {}
        ranking = trending.get("ranking") if isinstance(trending, dict) else None
        keyword_count = len(ranking) if isinstance(ranking, list) else 0

        top_domains = snapshot.top_domains or {}
        active_domain_users = 0
        if isinstance(top_domains, dict):
            for bucket in top_domains.values():
                if isinstance(bucket, dict):
                    active_domain_users += int(bucket.get("user_count", 0) or 0)

        axes = snapshot.global_8_axis_avg or {}
        has_axis_signal = any(
            float(value or 0) > 0 for value in axes.values() if value is not None
        )

        if keyword_count >= MIN_TRENDING_KEYWORDS:
            return True
        if active_domain_users >= MIN_DOMAIN_ACTIVE_USERS:
            return True
        return has_axis_signal

    @staticmethod
    def _is_graph_data_sufficient(snapshot: GlobalTrendsSnapshot) -> bool:
        """지식 그래프 생성 최소 데이터 — 도메인 허브 6개는 항상 생성 가능."""
        return TrendReportService._is_data_sufficient(snapshot)

    async def _invoke_gemini_report(self, compressed: CompressedSnapshot) -> str:
        client = get_client()
        user_prompt = build_report_user_prompt(compressed)
        response = await client.aio.models.generate_content(
            model=REPORTER_GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=MASTER_REPORT_SYSTEM_PROMPT,
                temperature=REPORTER_TEMPERATURE,
                max_output_tokens=REPORTER_MAX_OUTPUT_TOKENS,
            ),
        )
        return (response.text or "").strip()
