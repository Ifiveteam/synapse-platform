from __future__ import annotations

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    LayerB,
    ProfileInterpretation,
    Synapse8Axes,
)
from app.agents.profiler.subagent.scoring import top_axes

AXIS_LABELS: dict[str, str] = {
    "intellectual_curiosity": "지적 호기심",
    "practical_orientation": "실용 지향",
    "emotional_comfort": "정서·위로",
    "social_awareness": "사회·시선",
    "creative_expression": "창의·표현",
    "entertainment_release": "오락·해방",
    "self_improvement": "자기계발",
    "depth_immersion": "깊이·몰입",
}

LAYER_B_LABELS: dict[str, str] = {
    "search_active_ratio": "주체성",
    "viewing_concentration": "채널 편중도",
    "taste_diversity_index": "취향 다양성",
    "exploration_depth": "탐색 깊이",
}

SEARCH_ACTIVE_TARGET = 0.35
VIEWING_CONCENTRATION_TARGET = 0.45
TASTE_DIVERSITY_TARGET = 55.0
EXPLORATION_DEPTH_TARGET = 0.4


def _axis_label(key: str) -> str:
    return AXIS_LABELS.get(key, key)


def _consumption_mode(layer_b: LayerB) -> str:
    if layer_b.viewing_concentration >= 0.7 and layer_b.search_active_ratio < 0.25:
        return "편향형"
    if layer_b.search_active_ratio >= 0.3 and layer_b.exploration_depth >= 0.45:
        return "탐색형"
    if layer_b.viewing_concentration >= 0.55 and layer_b.exploration_depth < 0.35:
        return "습관형"
    return "균형형"


def _layer_b_improvement_gaps(layer_b: LayerB) -> dict[str, float]:
    return {
        "search_active_ratio": max(
            0.0, SEARCH_ACTIVE_TARGET - layer_b.search_active_ratio
        ),
        "viewing_concentration": max(
            0.0, layer_b.viewing_concentration - VIEWING_CONCENTRATION_TARGET
        ),
        "taste_diversity_index": max(
            0.0, (TASTE_DIVERSITY_TARGET - layer_b.taste_diversity_index) / 100
        ),
        "exploration_depth": max(
            0.0, EXPLORATION_DEPTH_TARGET - layer_b.exploration_depth
        ),
    }


def _primary_lever(layer_b: LayerB) -> str:
    gaps = _layer_b_improvement_gaps(layer_b)
    key = max(gaps, key=gaps.get)
    if gaps[key] <= 0.0:
        return LAYER_B_LABELS["search_active_ratio"]
    return LAYER_B_LABELS[key]


def _sovereignty_verdict(layer_b: LayerB) -> str:
    risk = 0
    if layer_b.viewing_concentration >= 0.75:
        risk += 2
    elif layer_b.viewing_concentration >= 0.55:
        risk += 1
    if layer_b.search_active_ratio < 0.2:
        risk += 1
    if layer_b.exploration_depth < 0.3:
        risk += 1
    if layer_b.taste_diversity_index < 40:
        risk += 1

    if risk >= 4:
        return "개선 권장"
    if risk >= 2:
        return "주의"
    return "양호"


def _radar_gap_insight(axes: Synapse8Axes, layer_b: LayerB) -> str:
    dominant = top_axes(axes, 1)[0]

    if axes.intellectual_curiosity >= 60 and layer_b.exploration_depth < 0.35:
        return (
            "지적 호기심 점수는 높지만 탐색 깊이가 낮아 "
            "새 주제를 얕게 훑는 패턴이 보입니다."
        )
    if axes.social_awareness >= 65 and layer_b.viewing_concentration >= 0.7:
        return "사회·시선 관심은 넓으나 채널 편중도가 높아 시청 출처가 좁습니다."
    if axes.depth_immersion >= 70 and layer_b.exploration_depth < 0.4:
        return "평소 몰입 성향은 강하지만 검색 기반 탐색 깊이는 상대적으로 낮습니다."
    if layer_b.taste_diversity_index < 40:
        return (
            f"취향 다양성이 낮고 {_axis_label(dominant)} 축이 두드러져 "
            "특정 영역에 쏠려 있습니다."
        )

    weak_key = min(SYNAPSE_AXIS_KEYS, key=lambda key: getattr(axes, key))
    return (
        f"레이더 상위 축({_axis_label(dominant)})과 "
        f"보완 축({_axis_label(weak_key)}) 사이 균형을 보며 "
        "소비 패턴을 조정할 여지가 있습니다."
    )


def compute_interpretation(
    axes: Synapse8Axes, layer_b: LayerB
) -> ProfileInterpretation:
    return ProfileInterpretation(
        consumption_mode=_consumption_mode(layer_b),
        primary_lever=_primary_lever(layer_b),
        sovereignty_verdict=_sovereignty_verdict(layer_b),
        radar_gap_insight=_radar_gap_insight(axes, layer_b),
    )
