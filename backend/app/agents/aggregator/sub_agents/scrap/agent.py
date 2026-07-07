"""Layer 1 — 스크랩 도메인 분류 에이전트."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.aggregator.schemas import (
    DomainDistributionSchema,
    DomainScoreMap,
    TrendMappingResult,
)
from app.agents.aggregator.sub_agents.base_agent import (
    DEFAULT_LLM_MODEL,
    BaseTrendAgent,
)
from app.agents.aggregator.sub_agents.scrap.prompts import SCRAP_SYSTEM_PROMPT
from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger
from app.models.trend_domain import TrendDomain

_TAG_MATCH_WEIGHT = 2.0
_CATEGORY_MATCH_WEIGHT = 1.0
_SEGMENT_SPLIT_RE = re.compile(r"[/|,·•\s]+")

_KEYWORD_RULES: tuple[tuple[tuple[str, ...], TrendDomain], ...] = (
    (
        (
            "기술",
            "ai",
            "개발",
            "it",
            "스타트업",
            "비즈니스",
            "경영",
            "소프트웨어",
            "프로그래밍",
            "코딩",
            "클라우드",
            "saas",
        ),
        TrendDomain.TECH_BUSINESS,
    ),
    (
        (
            "금융",
            "투자",
            "경제",
            "핀테크",
            "주식",
            "재테크",
            "은행",
            "자산",
            "부동산",
            "코인",
            "암호화폐",
        ),
        TrendDomain.ECONOMY_TECHFIN,
    ),
    (
        (
            "교육",
            "학습",
            "강의",
            "지식",
            "과학",
            "논문",
            "대학",
            "연구",
            "학술",
        ),
        TrendDomain.KNOWLEDGE_EDUCATION,
    ),
    (
        (
            "건강",
            "운동",
            "웰니스",
            "라이프",
            "여행",
            "음식",
            "뷰티",
            "카페",
            "요리",
            "다이어트",
            "명상",
        ),
        TrendDomain.LIFESTYLE_WELLNESS,
    ),
    (
        (
            "뉴스",
            "정치",
            "사회",
            "시사",
            "이슈",
            "정부",
            "정책",
            "선거",
            "외교",
        ),
        TrendDomain.SOCIAL_CURRENT_AFFAIRS,
    ),
    (
        (
            "영화",
            "음악",
            "게임",
            "엔터",
            "미디어",
            "유튜브",
            "k-pop",
            "kpop",
            "드라마",
            "예능",
            "아이돌",
            "웹툰",
        ),
        TrendDomain.CONTENT_MEDIA,
    ),
)


def _compact_text(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().casefold().replace(" ", "")


def _tokenize_segments(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    parts = _SEGMENT_SPLIT_RE.split(value.strip().casefold())
    return [part.replace(" ", "") for part in parts if part.replace(" ", "")]


def _domains_matching_text(text: str | None) -> set[TrendDomain]:
    compact = _compact_text(text)
    if not compact:
        return set()

    matched: set[TrendDomain] = set()
    for keywords, domain in _KEYWORD_RULES:
        for keyword in keywords:
            if keyword in compact:
                matched.add(domain)
                break
    return matched


def _format_tags(tags: list[Any] | None) -> str:
    if not tags:
        return "[]"
    normalized: list[str] = []
    for tag in tags:
        if isinstance(tag, str) and tag.strip():
            normalized.append(tag.strip())
    return json.dumps(normalized, ensure_ascii=False)


class ScrapDomainAgent(BaseTrendAgent):
    """스크랩 — tags/category 숏컷 후 Gemini LLM."""

    layer = "scrap"

    def __init__(self, agg_logger: AggregatorLogger | None = None) -> None:
        super().__init__(agg_logger)

    def _shortcut_scores(
        self,
        *,
        category: str | None,
        tags: list[str] | None,
    ) -> DomainScoreMap:
        raw_weights: dict[TrendDomain, float] = {}

        for tag in tags or []:
            if not isinstance(tag, str):
                continue
            for matched in _domains_matching_text(tag):
                raw_weights[matched] = raw_weights.get(matched, 0.0) + _TAG_MATCH_WEIGHT
            for segment in _tokenize_segments(tag):
                for matched in _domains_matching_text(segment):
                    raw_weights[matched] = (
                        raw_weights.get(matched, 0.0) + _TAG_MATCH_WEIGHT
                    )

        for segment in _tokenize_segments(category):
            for matched in _domains_matching_text(segment):
                raw_weights[matched] = (
                    raw_weights.get(matched, 0.0) + _CATEGORY_MATCH_WEIGHT
                )

        return self.normalize_scores(raw_weights)

    def _shortcut_keywords(
        self,
        *,
        category: str | None,
        tags: list[str] | None,
        title: str | None,
    ) -> list[str]:
        """숏컷 경로 — 구조화된 tags/title/category에서 키워드 후보 추출."""
        picks: list[str] = []
        for tag in tags or []:
            if isinstance(tag, str) and tag.strip():
                picks.append(tag.strip())
        if title and title.strip():
            picks.append(title.strip())
        if category and category.strip():
            picks.append(category.strip())
        return self.normalize_trend_keywords(picks)

    async def map_domain(
        self,
        *,
        category: str | None = None,
        tags: list[str] | None = None,
        title: str | None = None,
        summary: str | None = None,
        **_: Any,
    ) -> TrendMappingResult:
        timer_key = self._log.begin_timer(self.layer, "shortcut")
        shortcut_scores = self._shortcut_scores(category=category, tags=tags)
        shortcut_latency = self._log.end_timer(timer_key)

        if shortcut_scores and not self.is_score_distribution_ambiguous(
            shortcut_scores
        ):
            distribution = DomainDistributionSchema.from_scores(shortcut_scores)
            keywords = self._shortcut_keywords(
                category=category,
                tags=tags,
                title=title,
            )
            self._log.log_shortcut_hit(
                self.layer,
                latency_ms=shortcut_latency,
                result_summary=self._log.summarize_scores(distribution.scores),
                category=category,
                trend_keywords=keywords,
            )
            return TrendMappingResult(
                distribution=distribution,
                trend_keywords=keywords,
            )

        reason = "unmapped" if not shortcut_scores else "ambiguous_shortcut"
        user_content = (
            f"category: {category or ''}\n"
            f"tags: {_format_tags(tags)}\n"
            f"title: {title or ''}\n"
            f"summary: {summary or ''}"
        )
        distribution, _confidence, keywords = await self.invoke_llm_classifier(
            system_instruction=SCRAP_SYSTEM_PROMPT,
            user_content=user_content,
            model=DEFAULT_LLM_MODEL,
            reason=reason,
            category=category,
        )
        return TrendMappingResult(
            distribution=distribution,
            trend_keywords=keywords,
        )
