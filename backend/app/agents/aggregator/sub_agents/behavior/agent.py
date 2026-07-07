"""Layer 3 — 익스텐션 행동 로그 도메인 분류 에이전트."""

from __future__ import annotations

from typing import Any

from google.genai import types

from app.agents.aggregator.schemas import TrendMappingResult
from app.agents.aggregator.sub_agents.base_agent import (
    DEFAULT_LLM_MODEL,
    BaseTrendAgent,
)
from app.agents.aggregator.sub_agents.behavior.prompts import (
    BEHAVIOR_GROUNDING_SYSTEM_PROMPT,
    BEHAVIOR_SYSTEM_PROMPT,
)
from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger
from app.agents.archiver.core.tools import GOOGLE_SEARCH_TOOL
from app.agents.shared.gemini import get_client


class BehaviorDomainAgent(BaseTrendAgent):
    """익스텐션 로그 — 1차 LLM, 2차 Google Search Grounding."""

    layer = "behavior"

    def __init__(self, agg_logger: AggregatorLogger | None = None) -> None:
        super().__init__(agg_logger)

    async def _invoke_grounding_context(
        self,
        *,
        url: str,
        domain: str | None,
        page_title: str | None,
    ) -> str:
        self._log.log_grounding_invoked(
            self.layer,
            reason="low_confidence_or_ambiguous",
            url=url,
            domain=domain,
            page_title=page_title,
        )
        timer_key = self._log.begin_timer(self.layer, "grounding")
        prompt = (
            "다음 웹 페이지의 실제 콘텐츠 맥락을 파악해 거시 트렌드 분류에 필요한 "
            "핵심 주제·산업·콘텐츠 성격을 한국어로 요약하세요.\n"
            f"URL: {url}\n"
            f"Domain: {domain or ''}\n"
            f"Page title: {page_title or ''}"
        )
        client = get_client()
        response = await client.aio.models.generate_content(
            model=DEFAULT_LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You retrieve and summarize live web context for trend classification. "
                    "Respond in Korean."
                ),
                tools=[GOOGLE_SEARCH_TOOL],
                temperature=0.2,
            ),
        )
        latency_ms = self._log.end_timer(timer_key)
        grounding_text = (response.text or "").strip()
        self._log.log_success(
            self.layer,
            "grounding",
            latency_ms=latency_ms,
            result_summary=f"chars={len(grounding_text)}",
            url=url,
        )
        return grounding_text

    async def map_domain(
        self,
        *,
        domain: str | None = None,
        page_title: str | None = None,
        url: str | None = None,
        **_: Any,
    ) -> TrendMappingResult:
        if not domain and not page_title and not url:
            return TrendMappingResult.unmapped()

        user_content = (
            f"domain: {domain or ''}\npage_title: {page_title or ''}\nurl: {url or ''}"
        )

        distribution, confidence, keywords = await self.invoke_llm_classifier(
            system_instruction=BEHAVIOR_SYSTEM_PROMPT,
            user_content=user_content,
            model=DEFAULT_LLM_MODEL,
            reason="primary_llm",
            domain=domain,
            url=url,
        )

        if not self.needs_grounding(confidence, distribution):
            return TrendMappingResult(
                distribution=distribution,
                trend_keywords=keywords,
            )

        if not url or not url.strip():
            return TrendMappingResult(
                distribution=distribution,
                trend_keywords=keywords,
            )

        grounding_context = await self._invoke_grounding_context(
            url=url.strip(),
            domain=domain,
            page_title=page_title,
        )
        grounded_user_content = (
            f"{user_content}\n\n"
            f"--- Google Search Grounding context ---\n"
            f"{grounding_context}"
        )
        (
            grounded_distribution,
            _grounded_confidence,
            grounded_keywords,
        ) = await self.invoke_llm_classifier(
            system_instruction=BEHAVIOR_GROUNDING_SYSTEM_PROMPT,
            user_content=grounded_user_content,
            model=DEFAULT_LLM_MODEL,
            reason="grounding_refine",
            domain=domain,
            url=url,
        )
        if grounded_distribution.is_unmapped:
            return TrendMappingResult(
                distribution=distribution,
                trend_keywords=keywords,
            )
        return TrendMappingResult(
            distribution=grounded_distribution,
            trend_keywords=grounded_keywords,
        )
