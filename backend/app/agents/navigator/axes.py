"""Navigator 축 규칙 — 추출·보정·비교·페르소나 명칭 (순수 계산, LLM 없음).

이상향 설계(LLM)는 ideal.py, 이상향 13축 → 행동 8축 파생은 behavior_map.py.
"""

from __future__ import annotations

from app.agents.navigator.constants import (
    AXIS_MAX,
    AXIS_MIN,
    BEHAVIOR_AXES,
    DISPOSITION_AXES,
    DISPOSITION_LABELS_KO,
    INTEREST_DOMAINS,
    VALUES_TEMPERAMENT_AXES,
)
from app.agents.navigator.schemas import AxisGap, RadarComparison
from app.agents.profiler.axis_labels import SCORE_LABELS_KO

_KO_TO_DISPOSITION = {ko: en for en, ko in DISPOSITION_LABELS_KO.items()}


def clamp_value(value: float) -> float:
    return max(AXIS_MIN, min(AXIS_MAX, float(value)))


def clamp_scores(scores: dict[str, float]) -> dict[str, float]:
    return {axis: clamp_value(scores.get(axis, 0.0)) for axis in BEHAVIOR_AXES}


def clamp_disposition(scores: dict[str, float]) -> dict[str, float]:
    return {axis: clamp_value(scores.get(axis, 0.0)) for axis in DISPOSITION_AXES}


def disposition_from_portrait(portrait: dict | None) -> dict[str, float]:
    """portrait.disposition([{axis:한글라벨, value}]) → {영문키: 값}."""
    if not portrait:
        return {}
    out: dict[str, float] = {}
    for item in portrait.get("disposition") or []:
        en = _KO_TO_DISPOSITION.get(item.get("axis"))
        if en:
            out[en] = float(item.get("value") or 0.0)
    return out


def interest_from_portrait(portrait: dict | None) -> dict[str, float]:
    """portrait.interest([{axis:도메인, value}]) → {도메인: 값} (알려진 9개만)."""
    if not portrait:
        return {}
    return {
        item.get("axis"): float(item.get("value") or 0.0)
        for item in (portrait.get("interest") or [])
        if item.get("axis") in INTEREST_DOMAINS
    }


def coerce_interest_targets(items, current: dict[str, float]) -> dict[str, float]:
    """LLM이 낸 도메인 목표 목록(InterestTarget) → 9개 도메인 dict.

    누락 도메인은 현재값 유지, 미지 도메인은 버림, 전부 클램프.
    """
    out = dict(current)
    for it in items or []:
        domain = getattr(it, "domain", None)
        if domain in INTEREST_DOMAINS:
            out[domain] = clamp_value(getattr(it, "target", 0.0))
    return {d: clamp_value(out.get(d, 0.0)) for d in INTEREST_DOMAINS}


def clamp_values_13(values: dict[str, float]) -> dict[str, float]:
    return {
        axis: clamp_value(values.get(axis, 0.0)) for axis in VALUES_TEMPERAMENT_AXES
    }


def extract_8axis(profile_21: dict[str, float]) -> dict[str, float]:
    """21축 dict에서 행동 8축만 추출 (없으면 0.0)."""
    return {axis: float(profile_21.get(axis, 0.0)) for axis in BEHAVIOR_AXES}


def compare(
    current_8: dict[str, float],
    ideal_8: dict[str, float],
) -> RadarComparison:
    """현재 vs 이상향 축별 gap (순수 계산)."""
    gaps: list[AxisGap] = []
    gap_by_axis: dict[str, float] = {}
    for axis in BEHAVIOR_AXES:
        current = round(float(current_8.get(axis, 0.0)), 2)
        ideal = round(float(ideal_8.get(axis, 0.0)), 2)
        gap = round(ideal - current, 2)
        gap_by_axis[axis] = gap
        gaps.append(
            AxisGap(
                axis=axis,
                label_ko=SCORE_LABELS_KO.get(axis, axis),
                current=current,
                ideal=ideal,
                gap=gap,
            )
        )
    total_gap = round(sum(abs(v) for v in gap_by_axis.values()), 2)
    return RadarComparison(gaps=gaps, gap_by_axis=gap_by_axis, total_gap=total_gap)
