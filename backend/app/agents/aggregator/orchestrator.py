"""어그리게이터 도메인 매핑 오케스트레이터 — 3개 서브 에이전트 총괄."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.schemas import (
    DomainDistributionSchema,
    DomainScoreMap,
    TrendMappingResult,
)
from app.agents.aggregator.sub_agents.behavior.agent import BehaviorDomainAgent
from app.agents.aggregator.sub_agents.scrap.agent import ScrapDomainAgent
from app.agents.aggregator.sub_agents.youtube.agent import YoutubeDomainAgent
from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger


class AggregatorOrchestrator:
    """배치 엔진 진입점 — Scrap / YouTube / Behavior 서브 에이전트 위임."""

    def __init__(self, agg_logger: AggregatorLogger | None = None) -> None:
        logger = agg_logger or AggregatorLogger()
        self._log = logger
        self._scrap_agent = ScrapDomainAgent(logger)
        self._youtube_agent = YoutubeDomainAgent(logger)
        self._behavior_agent = BehaviorDomainAgent(logger)

    @staticmethod
    def is_unmapped(distribution: DomainDistributionSchema | DomainScoreMap) -> bool:
        if isinstance(distribution, DomainDistributionSchema):
            return distribution.is_unmapped
        return not distribution

    @staticmethod
    def _as_scores(distribution: DomainDistributionSchema) -> DomainScoreMap:
        return distribution.scores

    async def map_scrap(
        self,
        *,
        category: str | None,
        tags: list[str] | None,
        title: str | None,
        summary: str | None,
    ) -> TrendMappingResult:
        return await self._scrap_agent.map_domain(
            category=category,
            tags=tags,
            title=title,
            summary=summary,
        )

    async def map_youtube(
        self,
        *,
        youtube_category_id: str | None,
        title: str | None,
        tags: list[Any] | None,
        description: str | None,
        summary_kr: str | None,
    ) -> TrendMappingResult:
        return await self._youtube_agent.map_domain(
            youtube_category_id=youtube_category_id,
            title=title,
            tags=tags,
            description=description,
            summary_kr=summary_kr,
        )

    async def map_behavior(
        self,
        *,
        domain: str | None,
        page_title: str | None,
        url: str | None,
    ) -> TrendMappingResult:
        return await self._behavior_agent.map_domain(
            domain=domain,
            page_title=page_title,
            url=url,
        )

    async def map_scrap_row(self, row: object) -> TrendMappingResult:
        return await self.map_scrap(
            category=ScrapDomainAgent.row_field(row, "category"),
            tags=ScrapDomainAgent.row_field(row, "tags"),
            title=ScrapDomainAgent.row_field(row, "title"),
            summary=ScrapDomainAgent.row_field(row, "summary"),
        )

    async def map_youtube_row(
        self,
        catalog_row: object,
        analysis_row: object | None = None,
    ) -> TrendMappingResult:
        tags = YoutubeDomainAgent.row_field(catalog_row, "tags")
        summary_kr = None
        if analysis_row is not None:
            summary_kr = YoutubeDomainAgent.row_field(analysis_row, "summary_kr")

        category_id = YoutubeDomainAgent.row_field(catalog_row, "youtube_category_id")
        return await self.map_youtube(
            youtube_category_id=str(category_id) if category_id is not None else None,
            title=YoutubeDomainAgent.row_field(catalog_row, "title"),
            tags=tags if isinstance(tags, list) else None,
            description=YoutubeDomainAgent.row_field(catalog_row, "description"),
            summary_kr=summary_kr,
        )

    async def map_behavior_row(self, row: object) -> TrendMappingResult:
        return await self.map_behavior(
            domain=BehaviorDomainAgent.row_field(row, "domain"),
            page_title=BehaviorDomainAgent.row_field(row, "page_title"),
            url=BehaviorDomainAgent.row_field(row, "url"),
        )

    async def map_scrap_row_scores(self, row: object) -> DomainScoreMap:
        return self._as_scores((await self.map_scrap_row(row)).distribution)

    async def map_youtube_row_scores(
        self,
        catalog_row: object,
        analysis_row: object | None = None,
    ) -> DomainScoreMap:
        return self._as_scores(
            (await self.map_youtube_row(catalog_row, analysis_row)).distribution
        )

    async def map_behavior_row_scores(self, row: object) -> DomainScoreMap:
        return self._as_scores((await self.map_behavior_row(row)).distribution)


_default_orchestrator = AggregatorOrchestrator()


async def map_scrap_row(row: object) -> DomainScoreMap:
    return await _default_orchestrator.map_scrap_row_scores(row)


async def map_youtube_row(
    catalog_row: object,
    analysis_row: object | None = None,
) -> DomainScoreMap:
    return await _default_orchestrator.map_youtube_row_scores(catalog_row, analysis_row)


async def map_behavior_row(row: object) -> DomainScoreMap:
    return await _default_orchestrator.map_behavior_row_scores(row)
