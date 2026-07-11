"""키워드 벡터 Top-K semantic edge 빌더 (CPU bound — to_thread 호출 전제)."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations

from app.agents.aggregator.semantic.hints import KeywordHint

TAU_FLOOR = float(os.getenv("AGGREGATOR_SEMANTIC_TAU_FLOOR", "0.80"))
TAU_PERCENTILE = float(os.getenv("AGGREGATOR_SEMANTIC_TAU_PERCENTILE", "0.55"))
TOP_K = int(os.getenv("AGGREGATOR_SEMANTIC_TOP_K", "3"))
STRONG_CO_RAW = float(os.getenv("AGGREGATOR_SEMANTIC_STRONG_CO", "2.0"))


@dataclass(frozen=True)
class SemanticEdge:
    source: str
    target: str
    similarity: float
    left_hint: str
    right_hint: str
    boosted_cooccurrence: bool = False

    def to_json(self) -> dict[str, str | float | bool]:
        left, right = sorted((self.source, self.target))
        return {
            "source": left,
            "target": right,
            "similarity": round(self.similarity, 4),
            "link_type": "semantic",
            "left_hint": self.left_hint,
            "right_hint": self.right_hint,
            "boosted_cooccurrence": self.boosted_cooccurrence,
        }


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = 0.0
    norm_l = 0.0
    norm_r = 0.0
    for a, b in zip(left, right, strict=True):
        fa = float(a)
        fb = float(b)
        dot += fa * fb
        norm_l += fa * fa
        norm_r += fb * fb
    denom = math.sqrt(norm_l) * math.sqrt(norm_r)
    if denom <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / denom))


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    clamped = max(0.0, min(1.0, q))
    idx = clamped * (len(ordered) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return ordered[lo]
    frac = idx - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def dynamic_tau(similarities: Sequence[float]) -> float:
    """하한 τ + 분포 퍼센타일 보정."""
    if not similarities:
        return TAU_FLOOR
    pct = _percentile(similarities, TAU_PERCENTILE)
    return max(TAU_FLOOR, min(0.92, pct))


def build_semantic_edges(
    *,
    hints: Sequence[KeywordHint],
    vectors: Mapping[str, Sequence[float]],
    co_matrix: Mapping[tuple[str, str], float],
    top_k: int = TOP_K,
    tau_floor: float = TAU_FLOOR,
    strong_co_raw: float = STRONG_CO_RAW,
) -> list[SemanticEdge]:
    """τ 하한 + 다이내믹 τ + per-node Top-K + 강한 공출현 충돌 처리.

    CPU-bound — 호출부는 ``asyncio.to_thread`` 로 감싼다.
    """
    items: list[tuple[KeywordHint, Sequence[float]]] = []
    for hint in hints:
        vector = vectors.get(hint.embedding_text)
        if vector is None:
            continue
        items.append((hint, vector))

    if len(items) < 2:
        return []

    pair_sims: list[tuple[str, str, float, str, str]] = []
    for (hint_a, vec_a), (hint_b, vec_b) in combinations(items, 2):
        if hint_a.keyword == hint_b.keyword:
            continue
        sim = cosine_similarity(vec_a, vec_b)
        pair_sims.append(
            (
                hint_a.keyword,
                hint_b.keyword,
                sim,
                hint_a.hint_label,
                hint_b.hint_label,
            )
        )

    if not pair_sims:
        return []

    sims = [row[2] for row in pair_sims]
    tau = max(tau_floor, dynamic_tau(sims))
    eligible = [row for row in pair_sims if row[2] >= tau]
    if not eligible:
        return []

    by_node: dict[str, list[tuple[str, float, str, str]]] = {}
    for left, right, sim, left_hint, right_hint in eligible:
        by_node.setdefault(left, []).append((right, sim, left_hint, right_hint))
        by_node.setdefault(right, []).append((left, sim, right_hint, left_hint))

    selected: dict[tuple[str, str], SemanticEdge] = {}
    k = max(1, top_k)
    for node, neighbors in by_node.items():
        neighbors.sort(key=lambda item: item[1], reverse=True)
        for other, sim, hint_a, hint_b in neighbors[:k]:
            edge_key = tuple(sorted((node, other)))
            co_weight = float(co_matrix.get(edge_key, 0.0) or 0.0)
            if co_weight >= strong_co_raw:
                # 강한 팩트(공출현)가 있으면 semantic 엣지 생략
                continue
            existing = selected.get(edge_key)
            if existing is None or existing.similarity < sim:
                selected[edge_key] = SemanticEdge(
                    source=edge_key[0],
                    target=edge_key[1],
                    similarity=sim,
                    left_hint=hint_a,
                    right_hint=hint_b,
                    boosted_cooccurrence=False,
                )

    return list(selected.values())
