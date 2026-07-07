"""GlobalTrendsSnapshot + 에이전트 키워드 맵 → react-force-graph 표준 JSON 변환."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations
from typing import Any, Literal, TypedDict

from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.models.trend_domain import TrendDomain

# react-force-graph 바인딩용 노드·링크 타입
GraphNode = dict[str, str | float]
GraphLink = dict[str, str | float]
ForceGraphData = dict[str, list[GraphNode] | list[GraphLink]]

SourceType = Literal["scrap", "youtube", "behavior", "external", "user_daily"]


class AgentKeywordContext(TypedDict):
    """단일 소스 맥락에서 동시 출현한 키워드 묶음."""

    source: SourceType
    keywords: list[str]
    domains: list[str]


class AgentKeywordMap(TypedDict, total=False):
    """어그리게이터가 생성·스냅샷에 적재하는 당일 키워드 맥락 맵."""

    target_date: str
    contexts: list[AgentKeywordContext]
    keyword_domain_weights: dict[str, dict[str, float]]


class KnowledgeGraphMapper:
    """교차 도메인 동시 출현(Co-occurrence) 기반 지식 그래프 빌더.

    출력 구조는 react-force-graph가 추가 연산 없이 바인딩 가능한
    ``{"nodes": [...], "links": [...]}`` 형태이다.
    """

    DOMAIN_HUB_GROUP = "domain_hub"
    DEFAULT_TOP_KEYWORDS = 20

    # 노드·링크 시각화 스케일 (Min-Max 정규화 후 적용)
    NODE_VAL_MIN = 4.0
    NODE_VAL_MAX = 28.0
    LINK_VAL_MIN = 0.15
    LINK_VAL_MAX = 4.0
    DOMAIN_HUB_BASE_VAL = 22.0

    def map(
        self,
        snapshot: GlobalTrendsSnapshot,
        keyword_map: AgentKeywordMap | None = None,
    ) -> ForceGraphData:
        """스냅샷과 키워드 맵으로 force-graph 데이터를 생성한다."""
        resolved_map = keyword_map or self._keyword_map_from_snapshot(snapshot)
        top_keywords = self._extract_top_keywords(snapshot)
        domain_stats = self._extract_domain_stats(snapshot)

        keyword_scores = {
            row["keyword"]: float(row.get("score", 0.0) or 0.0) for row in top_keywords
        }
        keyword_domains = self._resolve_keyword_domains(resolved_map, top_keywords)

        co_matrix = self._build_cooccurrence_matrix(
            resolved_map,
            keyword_set=set(keyword_scores.keys()),
        )
        domain_affinity = self._build_keyword_domain_affinity(
            keyword_domains,
            domain_stats,
        )

        nodes = self._build_nodes(
            top_keywords=top_keywords,
            keyword_domains=keyword_domains,
            domain_stats=domain_stats,
        )
        links = self._build_links(
            top_keyword_ids=set(keyword_scores.keys()),
            co_matrix=co_matrix,
            domain_affinity=domain_affinity,
            domain_stats=domain_stats,
        )

        return {"nodes": nodes, "links": links}

    def map_with_meta(
        self,
        snapshot: GlobalTrendsSnapshot,
        keyword_map: AgentKeywordMap | None = None,
    ) -> tuple[ForceGraphData, dict[str, Any]]:
        """그래프 데이터와 메타 통계를 함께 반환한다."""
        graph = self.map(snapshot, keyword_map)
        nodes = graph["nodes"]
        links = graph["links"]
        meta = {
            "algorithm": "cross_domain_cooccurrence_v1",
            "node_count": len(nodes),
            "link_count": len(links),
            "domain_hub_count": sum(
                1 for node in nodes if node.get("group") == self.DOMAIN_HUB_GROUP
            ),
            "keyword_node_count": sum(
                1 for node in nodes if node.get("group") != self.DOMAIN_HUB_GROUP
            ),
        }
        return graph, meta

    @staticmethod
    def _keyword_map_from_snapshot(
        snapshot: GlobalTrendsSnapshot,
    ) -> AgentKeywordMap:
        """스냅샷 JSONB에 적재된 keyword_context_map을 읽는다."""
        raw = getattr(snapshot, "keyword_context_map", None) or {}
        if not isinstance(raw, dict):
            return {"contexts": [], "keyword_domain_weights": {}}
        contexts = raw.get("contexts")
        weights = raw.get("keyword_domain_weights")
        return {
            "target_date": str(raw.get("target_date", "")),
            "contexts": contexts if isinstance(contexts, list) else [],
            "keyword_domain_weights": (weights if isinstance(weights, dict) else {}),
        }

    @classmethod
    def _extract_top_keywords(
        cls,
        snapshot: GlobalTrendsSnapshot,
        *,
        top_n: int | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """trending_keywords.ranking 상위 N개를 추출한다."""
        limit = top_n or cls.DEFAULT_TOP_KEYWORDS
        trending = snapshot.trending_keywords or {}
        if not isinstance(trending, dict):
            return []
        ranking = trending.get("ranking")
        if not isinstance(ranking, list):
            return []
        rows: list[dict[str, Any]] = []
        for row in ranking:
            if not isinstance(row, dict):
                continue
            keyword = str(row.get("keyword", "")).strip()
            if not keyword:
                continue
            score = float(row.get("score", 0.0) or 0.0)
            if score < min_score:
                continue
            rows.append(
                {
                    "keyword": keyword,
                    "score": score,
                    "count_today": int(row.get("count_today", 0) or 0),
                    "rank": int(row.get("rank", 0) or 0),
                }
            )
        rows.sort(key=lambda item: float(item["score"]), reverse=True)
        return rows[:limit]

    @staticmethod
    def _extract_domain_stats(
        snapshot: GlobalTrendsSnapshot,
    ) -> dict[str, dict[str, float]]:
        """6대 도메인 집계 수치를 정규화-friendly dict로 변환한다."""
        top_domains = snapshot.top_domains or {}
        stats: dict[str, dict[str, float]] = {}
        for domain in TrendDomain:
            bucket = top_domains.get(domain.value)
            if not isinstance(bucket, dict):
                stats[domain.value] = {
                    "user_count": 0.0,
                    "total_duration": 0.0,
                    "avg_weight": 0.0,
                }
                continue
            stats[domain.value] = {
                "user_count": float(bucket.get("user_count", 0) or 0),
                "total_duration": float(bucket.get("total_duration", 0) or 0),
                "avg_weight": float(bucket.get("avg_weight", 0.0) or 0.0),
            }
        return stats

    @classmethod
    def _resolve_keyword_domains(
        cls,
        keyword_map: AgentKeywordMap,
        top_keywords: Sequence[Mapping[str, Any]],
    ) -> dict[str, str]:
        """키워드별 대표 TrendDomain(group)을 결정한다."""
        weights = keyword_map.get("keyword_domain_weights") or {}
        result: dict[str, str] = {}

        for row in top_keywords:
            keyword = str(row["keyword"])
            domain_weights = weights.get(keyword)
            if isinstance(domain_weights, dict) and domain_weights:
                primary = max(
                    domain_weights.items(),
                    key=lambda item: float(item[1] or 0.0),
                )[0]
                result[keyword] = primary
                continue

            # 맵에 없으면 컨텍스트 domains 빈도로 추론
            domain_votes: dict[str, int] = defaultdict(int)
            for context in keyword_map.get("contexts") or []:
                if not isinstance(context, dict):
                    continue
                kws = context.get("keywords") or []
                if keyword not in kws:
                    continue
                for domain in context.get("domains") or []:
                    if domain:
                        domain_votes[str(domain)] += 1
            if domain_votes:
                result[keyword] = max(domain_votes.items(), key=lambda x: x[1])[0]
            else:
                result[keyword] = TrendDomain.TECH_BUSINESS.value

        return result

    @classmethod
    def _build_cooccurrence_matrix(
        cls,
        keyword_map: AgentKeywordMap,
        *,
        keyword_set: set[str],
    ) -> dict[tuple[str, str], float]:
        """맥락 단위 동시 출현 빈도 → 대칭 co-occurrence 매트릭스."""
        if not keyword_set:
            return {}

        matrix: dict[tuple[str, str], float] = defaultdict(float)
        contexts = keyword_map.get("contexts") or []

        for context in contexts:
            if not isinstance(context, dict):
                continue
            raw_keywords = context.get("keywords") or []
            # 상위 키워드 집합과 교집합 — Set 연산으로 후보 축소
            present = {str(kw).strip() for kw in raw_keywords if str(kw).strip()}
            present &= keyword_set
            if len(present) < 2:
                continue

            # 소스 가중치: 동일 유저 일별 묶음 > 행동/스크랩 > 외부
            source = str(context.get("source", ""))
            source_weight = cls._source_weight(source)

            for left, right in combinations(sorted(present), 2):
                matrix[(left, right)] += source_weight

        return dict(matrix)

    @staticmethod
    def _source_weight(source: str) -> float:
        """소스 유형별 동시 출현 신뢰 가중치."""
        weights = {
            "user_daily": 1.5,
            "scrap": 1.2,
            "youtube": 1.1,
            "behavior": 1.0,
            "external": 0.85,
        }
        return weights.get(source, 1.0)

    @classmethod
    def _build_keyword_domain_affinity(
        cls,
        keyword_domains: Mapping[str, str],
        domain_stats: Mapping[str, Mapping[str, float]],
    ) -> dict[tuple[str, str], float]:
        """키워드 → 도메인 허브 엣지 가중치 (키워드 도메인 + 플랫폼 가중치 결합)."""
        affinity: dict[tuple[str, str], float] = {}
        for keyword, domain in keyword_domains.items():
            stats = domain_stats.get(domain, {})
            avg_weight = float(stats.get("avg_weight", 0.0) or 0.0)
            user_count = float(stats.get("user_count", 0.0) or 0.0)
            # 도메인 매칭 1.0 + 플랫폼 활성도 보정
            score = 1.0 + avg_weight + math.log1p(user_count) * 0.05
            affinity[(keyword, domain)] = score
        return affinity

    @classmethod
    def _build_nodes(
        cls,
        *,
        top_keywords: Sequence[Mapping[str, Any]],
        keyword_domains: Mapping[str, str],
        domain_stats: Mapping[str, Mapping[str, float]],
        active_domains: frozenset[str] | None = None,
    ) -> list[GraphNode]:
        """6대 도메인 허브 + 급상승 키워드 노드를 생성한다."""
        nodes: list[GraphNode] = []
        domain_list = (
            [domain for domain in TrendDomain if domain.value in active_domains]
            if active_domains
            else list(TrendDomain)
        )

        # 도메인 허브 — 센터 앵커 (val은 avg_weight·user_count 기반)
        domain_raw_vals = [
            float(domain_stats.get(domain.value, {}).get("avg_weight", 0.0) or 0.0)
            + math.log1p(
                float(domain_stats.get(domain.value, {}).get("user_count", 0.0) or 0.0)
            )
            * 0.1
            for domain in domain_list
        ]
        domain_vals = cls._min_max_scale(
            domain_raw_vals,
            cls.NODE_VAL_MIN,
            cls.NODE_VAL_MAX,
            fallback=cls.DOMAIN_HUB_BASE_VAL,
        )
        for index, domain in enumerate(domain_list):
            nodes.append(
                {
                    "id": domain.value,
                    "group": cls.DOMAIN_HUB_GROUP,
                    "val": round(domain_vals[index], 4),
                }
            )

        # 급상승 키워드 노드
        keyword_scores = [float(row.get("score", 0.0) or 0.0) for row in top_keywords]
        keyword_vals = cls._min_max_scale(
            keyword_scores,
            cls.NODE_VAL_MIN,
            cls.NODE_VAL_MAX,
            fallback=8.0,
        )
        for index, row in enumerate(top_keywords):
            keyword = str(row["keyword"])
            nodes.append(
                {
                    "id": keyword,
                    "group": keyword_domains.get(
                        keyword, TrendDomain.TECH_BUSINESS.value
                    ),
                    "val": round(keyword_vals[index], 4),
                }
            )

        return nodes

    @classmethod
    def _build_links(
        cls,
        *,
        top_keyword_ids: set[str],
        co_matrix: Mapping[tuple[str, str], float],
        domain_affinity: Mapping[tuple[str, str], float],
        domain_stats: Mapping[str, Mapping[str, float]],
        active_domains: frozenset[str] | None = None,
    ) -> list[GraphLink]:
        """키워드↔키워드·키워드↔도메인·도메인↔도메인 링크를 생성한다."""
        links: list[GraphLink] = []
        seen: set[tuple[str, str]] = set()

        def _append_link(source: str, target: str, raw_value: float) -> None:
            if source == target:
                return
            edge = tuple(sorted((source, target)))
            if edge in seen:
                return
            seen.add(edge)
            links.append(
                {
                    "source": edge[0],
                    "target": edge[1],
                    "value": raw_value,
                }
            )

        # 1) 키워드 간 co-occurrence
        co_values = list(co_matrix.values())
        scaled_co = cls._min_max_scale(
            co_values,
            cls.LINK_VAL_MIN,
            cls.LINK_VAL_MAX,
            fallback=cls.LINK_VAL_MIN,
        )
        for index, ((left, right), _raw) in enumerate(co_matrix.items()):
            if left not in top_keyword_ids or right not in top_keyword_ids:
                continue
            if scaled_co[index] < cls.LINK_VAL_MIN:
                continue
            _append_link(left, right, scaled_co[index])

        # 2) 키워드 → 도메인 허브
        affinity_values = list(domain_affinity.values())
        scaled_affinity = cls._min_max_scale(
            affinity_values,
            cls.LINK_VAL_MIN,
            cls.LINK_VAL_MAX,
            fallback=cls.LINK_VAL_MIN,
        )
        for index, ((keyword, domain), _raw) in enumerate(domain_affinity.items()):
            if keyword not in top_keyword_ids:
                continue
            _append_link(keyword, domain, scaled_affinity[index])

        # 3) 도메인 허브 간 약한 상호 연결 (플랫폼 거시 흐름)
        domain_ids = (
            [domain.value for domain in TrendDomain if domain.value in active_domains]
            if active_domains
            else [domain.value for domain in TrendDomain]
        )
        domain_pairs: list[tuple[str, str]] = []
        pair_weights: list[float] = []
        for left, right in combinations(domain_ids, 2):
            left_w = float(domain_stats.get(left, {}).get("avg_weight", 0.0) or 0.0)
            right_w = float(domain_stats.get(right, {}).get("avg_weight", 0.0) or 0.0)
            weight = (left_w + right_w) / 2.0
            if weight <= 0:
                continue
            domain_pairs.append((left, right))
            pair_weights.append(weight)

        scaled_domain = cls._min_max_scale(
            pair_weights,
            cls.LINK_VAL_MIN * 0.6,
            cls.LINK_VAL_MAX * 0.5,
            fallback=cls.LINK_VAL_MIN * 0.6,
        )
        for index, (left, right) in enumerate(domain_pairs):
            _append_link(left, right, scaled_domain[index])

        # value 필드 최종 반올림
        for link in links:
            link["value"] = round(float(link["value"]), 4)

        return links

    @staticmethod
    def _min_max_scale(
        values: Sequence[float],
        out_min: float,
        out_max: float,
        *,
        fallback: float,
    ) -> list[float]:
        """Min-Max Scaling — 단일 값·상수열은 fallback으로 대체."""
        if not values:
            return []
        vmin = min(values)
        vmax = max(values)
        if math.isclose(vmin, vmax):
            return [fallback for _ in values]
        span = vmax - vmin
        return [
            out_min + ((value - vmin) / span) * (out_max - out_min) for value in values
        ]

    def map_simulation(
        self,
        snapshot_like: Any,
        keyword_map: AgentKeywordMap | None = None,
        *,
        target_domains: Sequence[str] | None = None,
        min_score_threshold: float = 0.0,
        top_n: int | None = None,
    ) -> tuple[ForceGraphData, dict[str, Any]]:
        """필터 조건을 적용해 On-the-fly 지식 그래프를 재연산한다."""
        resolved_map = keyword_map or self._keyword_map_from_snapshot(snapshot_like)
        active_domains = self._normalize_target_domains(target_domains)

        if active_domains:
            resolved_map = self._filter_keyword_map_by_domains(
                resolved_map,
                active_domains,
            )

        top_keywords = self._extract_top_keywords(
            snapshot_like,
            top_n=top_n,
            min_score=min_score_threshold,
        )
        domain_stats = self._extract_domain_stats(snapshot_like)

        if active_domains:
            domain_stats = {
                domain: domain_stats.get(domain, self._empty_domain_bucket())
                for domain in active_domains
            }
            top_keywords = [
                row
                for row in top_keywords
                if self._resolve_keyword_domains(resolved_map, [row]).get(
                    str(row["keyword"]),
                    TrendDomain.TECH_BUSINESS.value,
                )
                in active_domains
            ]

        keyword_scores = {
            row["keyword"]: float(row.get("score", 0.0) or 0.0) for row in top_keywords
        }
        keyword_domains = self._resolve_keyword_domains(resolved_map, top_keywords)

        co_matrix = self._build_cooccurrence_matrix(
            resolved_map,
            keyword_set=set(keyword_scores.keys()),
        )
        domain_affinity = self._build_keyword_domain_affinity(
            keyword_domains,
            domain_stats,
        )

        nodes = self._build_nodes(
            top_keywords=top_keywords,
            keyword_domains=keyword_domains,
            domain_stats=domain_stats,
            active_domains=active_domains,
        )
        links = self._build_links(
            top_keyword_ids=set(keyword_scores.keys()),
            co_matrix=co_matrix,
            domain_affinity=domain_affinity,
            domain_stats=domain_stats,
            active_domains=active_domains,
        )
        graph: ForceGraphData = {"nodes": nodes, "links": links}
        meta = {
            "algorithm": "cross_domain_cooccurrence_simulator_v1",
            "node_count": len(nodes),
            "link_count": len(links),
            "domain_hub_count": sum(
                1 for node in nodes if node.get("group") == self.DOMAIN_HUB_GROUP
            ),
            "keyword_node_count": sum(
                1 for node in nodes if node.get("group") != self.DOMAIN_HUB_GROUP
            ),
            "min_score_threshold": min_score_threshold,
            "target_domains": list(active_domains) if active_domains else [],
        }
        return graph, meta

    @staticmethod
    def _empty_domain_bucket() -> dict[str, float]:
        return {"user_count": 0.0, "total_duration": 0.0, "avg_weight": 0.0}

    @classmethod
    def _normalize_target_domains(
        cls,
        target_domains: Sequence[str] | None,
    ) -> frozenset[str] | None:
        if not target_domains:
            return None
        allowed = {domain.value for domain in TrendDomain}
        normalized = {
            str(domain).strip()
            for domain in target_domains
            if str(domain).strip() in allowed
        }
        return frozenset(normalized) if normalized else None

    @classmethod
    def _filter_keyword_map_by_domains(
        cls,
        keyword_map: AgentKeywordMap,
        active_domains: frozenset[str],
    ) -> AgentKeywordMap:
        filtered_contexts: list[AgentKeywordContext] = []
        for context in keyword_map.get("contexts") or []:
            if not isinstance(context, dict):
                continue
            domains = {
                str(domain).strip()
                for domain in (context.get("domains") or [])
                if str(domain).strip()
            }
            if domains and domains.isdisjoint(active_domains):
                continue
            filtered_contexts.append(context)  # type: ignore[arg-type]

        filtered_weights: dict[str, dict[str, float]] = {}
        for keyword, domain_weights in (
            keyword_map.get("keyword_domain_weights") or {}
        ).items():
            if not isinstance(domain_weights, dict):
                continue
            kept = {
                str(domain): float(weight)
                for domain, weight in domain_weights.items()
                if str(domain) in active_domains and float(weight or 0) > 0
            }
            if kept:
                filtered_weights[str(keyword)] = kept

        return {
            "target_date": keyword_map.get("target_date", ""),
            "contexts": filtered_contexts,
            "keyword_domain_weights": filtered_weights,
        }


def build_keyword_context_map(
    *,
    target_date: str,
    contexts: Iterable[Mapping[str, Any]],
    keyword_domain_weights: Mapping[str, Mapping[str, float]],
) -> AgentKeywordMap:
    """어그리게이터 배치 종료 시 스냅샷에 적재할 키워드 맵 페이로드를 조립한다."""
    normalized_contexts: list[AgentKeywordContext] = []
    for context in contexts:
        source = str(context.get("source", "scrap"))
        keywords = [
            str(kw).strip() for kw in (context.get("keywords") or []) if str(kw).strip()
        ]
        if len(keywords) < 2:
            continue
        domains = [
            str(domain).strip()
            for domain in (context.get("domains") or [])
            if str(domain).strip()
        ]
        normalized_contexts.append(
            {
                "source": source,  # type: ignore[typeddict-item]
                "keywords": keywords,
                "domains": domains,
            }
        )

    weights: dict[str, dict[str, float]] = {}
    for keyword, domain_map in keyword_domain_weights.items():
        clean_key = str(keyword).strip()
        if not clean_key or not isinstance(domain_map, Mapping):
            continue
        weights[clean_key] = {
            str(domain): round(float(weight), 6)
            for domain, weight in domain_map.items()
            if float(weight or 0) > 0
        }

    return {
        "target_date": target_date,
        "contexts": normalized_contexts,
        "keyword_domain_weights": weights,
    }
