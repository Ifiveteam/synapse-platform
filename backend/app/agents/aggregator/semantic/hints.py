"""힌트 결합 키워드 — semantic 임베딩 단위."""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.models.trend_domain import TrendDomain

# behavior/external 보강이 목표이므로 동률 시 이쪽을 선호
SOURCE_PRIORITY: tuple[str, ...] = (
    "behavior",
    "external",
    "scrap",
    "youtube",
    "user_daily",
    "mixed",
)

DEFAULT_DOMAIN = TrendDomain.TECH_BUSINESS.value
DEFAULT_TOP_N = int(os.getenv("AGGREGATOR_SEMANTIC_TOP_N", "30"))
DEFAULT_MAX_CANDIDATES = int(os.getenv("AGGREGATOR_SEMANTIC_MAX_CANDIDATES", "60"))


@dataclass(frozen=True)
class KeywordHint:
    """임베딩 단위 — raw keyword + 소스/도메인 힌트."""

    keyword: str
    hint_source: str
    hint_domain: str

    @property
    def embedding_text(self) -> str:
        return f"[{self.hint_source}|{self.hint_domain}] {self.keyword}"

    @property
    def hint_label(self) -> str:
        return f"{self.hint_source}|{self.hint_domain}"


def resolve_hint(
    keyword: str,
    *,
    domain_weights: Mapping[str, Mapping[str, float]],
    contexts: Sequence[Mapping[str, Any]],
    default_domain: str = DEFAULT_DOMAIN,
) -> KeywordHint:
    """키워드별 대표 소스·도메인을 결정한다."""
    weights = domain_weights.get(keyword) or {}
    if weights:
        hint_domain = max(
            weights.items(),
            key=lambda item: float(item[1] or 0.0),
        )[0]
    else:
        hint_domain = default_domain

    votes: Counter[str] = Counter()
    for context in contexts:
        raw_keywords = context.get("keywords") or []
        present = {str(kw).strip() for kw in raw_keywords if str(kw).strip()}
        if keyword not in present:
            continue
        source = str(context.get("source") or "mixed").strip() or "mixed"
        votes[source] += 1

    if votes:
        best_count = max(votes.values())
        tied = [source for source, count in votes.items() if count == best_count]
        hint_source = next(
            (source for source in SOURCE_PRIORITY if source in tied),
            tied[0],
        )
    else:
        hint_source = "mixed"

    return KeywordHint(
        keyword=keyword,
        hint_source=hint_source,
        hint_domain=str(hint_domain),
    )


def _normalize_keyword(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if len(cleaned) < 2:
        return None
    return cleaned


def _keywords_from_ranking(
    trending_keywords: Mapping[str, Any], top_n: int
) -> list[str]:
    ranking = trending_keywords.get("ranking")
    if not isinstance(ranking, list):
        return []
    out: list[str] = []
    for row in ranking:
        if not isinstance(row, Mapping):
            continue
        keyword = _normalize_keyword(row.get("keyword"))
        if keyword:
            out.append(keyword)
        if len(out) >= top_n:
            break
    return out


def _keywords_from_contexts(
    contexts: Sequence[Mapping[str, Any]],
    *,
    sources: frozenset[str],
) -> list[str]:
    out: list[str] = []
    for context in contexts:
        source = str(context.get("source") or "")
        if source not in sources:
            continue
        for raw in context.get("keywords") or []:
            keyword = _normalize_keyword(raw)
            if keyword:
                out.append(keyword)
    return out


def _keywords_from_external(external_market_keywords: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    by_domain = external_market_keywords.get("by_domain")
    if isinstance(by_domain, Mapping):
        for bucket in by_domain.values():
            if not isinstance(bucket, Mapping):
                continue
            for entry in bucket.get("google") or []:
                if isinstance(entry, Mapping):
                    keyword = _normalize_keyword(entry.get("keyword"))
                    if keyword:
                        out.append(keyword)
            for entry in bucket.get("naver") or []:
                if not isinstance(entry, Mapping):
                    continue
                group = _normalize_keyword(entry.get("group_name"))
                if group:
                    out.append(group)
                    continue
                raw = entry.get("keywords")
                if raw:
                    first = str(raw).replace("/", ",").split(",")[0]
                    keyword = _normalize_keyword(first)
                    if keyword:
                        out.append(keyword)

    raw = external_market_keywords.get("raw")
    if isinstance(raw, Mapping):
        for item in raw.get("google_trends") or []:
            if isinstance(item, Mapping):
                keyword = _normalize_keyword(item.get("keyword"))
                if keyword:
                    out.append(keyword)
    return out


def collect_keyword_hints(
    *,
    trending_keywords: Mapping[str, Any],
    keyword_context_map: Mapping[str, Any],
    external_market_keywords: Mapping[str, Any] | None = None,
    top_n: int = DEFAULT_TOP_N,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> list[KeywordHint]:
    """당일 semantic 임베딩 후보를 조립한다 (raw 로그 제외)."""
    contexts_raw = keyword_context_map.get("contexts") or []
    contexts: list[Mapping[str, Any]] = [
        ctx for ctx in contexts_raw if isinstance(ctx, Mapping)
    ]
    domain_weights_raw = keyword_context_map.get("keyword_domain_weights") or {}
    domain_weights: dict[str, Mapping[str, float]] = {
        str(key): value
        for key, value in domain_weights_raw.items()
        if isinstance(value, Mapping)
    }

    ordered: list[str] = []
    seen: set[str] = set()

    def _extend(values: Iterable[str]) -> None:
        for keyword in values:
            if keyword in seen:
                continue
            seen.add(keyword)
            ordered.append(keyword)
            if len(ordered) >= max_candidates:
                return

    _extend(_keywords_from_ranking(trending_keywords, top_n))
    if len(ordered) < max_candidates:
        _extend(
            _keywords_from_contexts(
                contexts,
                sources=frozenset({"behavior", "external"}),
            )
        )
    if len(ordered) < max_candidates and external_market_keywords:
        _extend(_keywords_from_external(external_market_keywords))

    return [
        resolve_hint(
            keyword,
            domain_weights=domain_weights,
            contexts=contexts,
        )
        for keyword in ordered
    ]
