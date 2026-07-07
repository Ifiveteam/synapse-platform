"""Layer 2 — YouTube 도메인 분류 에이전트."""

from __future__ import annotations

import json
from typing import Any

from app.agents.aggregator.schemas import DomainDistributionSchema, TrendMappingResult
from app.agents.aggregator.sub_agents.base_agent import (
    DEFAULT_LLM_MODEL,
    BaseTrendAgent,
)
from app.agents.aggregator.sub_agents.youtube.prompts import YOUTUBE_SYSTEM_PROMPT
from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger
from app.models.trend_domain import TrendDomain


def _format_tags(tags: list[Any] | None) -> str:
    if not tags:
        return "[]"
    normalized: list[str] = []
    for tag in tags:
        if isinstance(tag, str) and tag.strip():
            normalized.append(tag.strip())
    return json.dumps(normalized, ensure_ascii=False)


_CATEGORY_LABELS: dict[str, str] = {
    "1": "영화/애니메이션",
    "2": "자동차/교통",
    "10": "음악",
    "15": "애완동물/동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "20": "게임",
    "22": "인물/블로그",
    "23": "코미디",
    "24": "엔터테인먼트",
    "25": "뉴스/정치",
    "26": "노하우/스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "비영리/사회운동",
}

_SHORTCUT_CATEGORY_MAP: dict[str, TrendDomain] = {
    "28": TrendDomain.TECH_BUSINESS,
    "25": TrendDomain.SOCIAL_CURRENT_AFFAIRS,
    "27": TrendDomain.KNOWLEDGE_EDUCATION,
}

_LLM_CATEGORY_IDS: frozenset[str] = frozenset(
    {
        "1",
        "2",
        "10",
        "15",
        "17",
        "19",
        "20",
        "22",
        "23",
        "24",
        "26",
        "29",
    }
)


class YoutubeDomainAgent(BaseTrendAgent):
    """YouTube — 3개 categoryId 숏컷, 12개 LLM 정밀 분류."""

    layer = "youtube"

    def __init__(self, agg_logger: AggregatorLogger | None = None) -> None:
        super().__init__(agg_logger)

    def _shortcut_keywords(
        self,
        *,
        title: str | None,
        tags: list[Any] | None,
        category_label: str,
    ) -> list[str]:
        picks: list[str] = []
        for tag in tags or []:
            if isinstance(tag, str) and tag.strip():
                picks.append(tag.strip())
        if title and title.strip():
            picks.append(title.strip())
        if category_label and category_label != "unknown":
            picks.append(category_label)
        return self.normalize_trend_keywords(picks)

    async def map_domain(
        self,
        *,
        youtube_category_id: str | None = None,
        title: str | None = None,
        tags: list[Any] | None = None,
        description: str | None = None,
        summary_kr: str | None = None,
        **_: Any,
    ) -> TrendMappingResult:
        category_id = str(youtube_category_id).strip() if youtube_category_id else ""
        category_label = _CATEGORY_LABELS.get(category_id, "unknown")

        if category_id in _SHORTCUT_CATEGORY_MAP:
            timer_key = self._log.begin_timer(self.layer, "shortcut")
            domain = _SHORTCUT_CATEGORY_MAP[category_id]
            latency_ms = self._log.end_timer(timer_key)
            distribution = DomainDistributionSchema.single(domain)
            keywords = self._shortcut_keywords(
                title=title,
                tags=tags if isinstance(tags, list) else None,
                category_label=category_label,
            )
            self._log.log_shortcut_hit(
                self.layer,
                latency_ms=latency_ms,
                result_summary=self._log.summarize_scores(distribution.scores),
                youtube_category_id=category_id,
                category_label=category_label,
                trend_keywords=keywords,
            )
            return TrendMappingResult(
                distribution=distribution,
                trend_keywords=keywords,
            )

        if category_id not in _LLM_CATEGORY_IDS and category_id:
            self._log.log_llm_invoked(
                self.layer,
                reason="unknown_category_id_fallback",
                youtube_category_id=category_id,
            )

        if not category_id and not any([title, tags, description, summary_kr]):
            return TrendMappingResult.unmapped()

        user_content = (
            f"youtube_category_id: {category_id}\n"
            f"youtube_category_label: {category_label}\n"
            f"title: {title or ''}\n"
            f"tags: {_format_tags(tags if isinstance(tags, list) else None)}\n"
            f"description: {description or ''}\n"
            f"summary_kr: {summary_kr or ''}"
        )
        distribution, _confidence, keywords = await self.invoke_llm_classifier(
            system_instruction=YOUTUBE_SYSTEM_PROMPT,
            user_content=user_content,
            model=DEFAULT_LLM_MODEL,
            reason="llm_required_category",
            youtube_category_id=category_id,
            category_label=category_label,
        )
        return TrendMappingResult(
            distribution=distribution,
            trend_keywords=keywords,
        )
