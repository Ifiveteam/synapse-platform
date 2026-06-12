from __future__ import annotations

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    LayerB,
    ProfileInterpretation,
    Synapse8Axes,
)
from app.agents.profiler.state import ProfilerState

_AXIS_LABELS: dict[str, str] = {
    "intellectual_curiosity": "지적 호기심",
    "practical_orientation": "실용 지향",
    "emotional_comfort": "정서·위로",
    "social_awareness": "사회·시선",
    "creative_expression": "창의·표현",
    "entertainment_release": "오락·해방",
    "self_improvement": "자기계발",
    "depth_immersion": "깊이·몰입",
}

def _top_axes(axes: Synapse8Axes, count: int = 2) -> list[str]:
    axis_values = [getattr(axes, key) for key in SYNAPSE_AXIS_KEYS]
    ranked = sorted(
        zip(SYNAPSE_AXIS_KEYS, axis_values, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    return [key for key, _ in ranked[:count]]


_LAYER_B_LABELS: dict[str, str] = {
    "search_active_ratio": "주체성",
    "viewing_concentration": "채널 편중도",
    "taste_diversity_index": "취향 다양성",
    "exploration_depth": "탐색 깊이",
}


def _compute_interpretation(
    axes: Synapse8Axes, layer_b: LayerB
) -> ProfileInterpretation:
    if layer_b.viewing_concentration >= 0.7 and layer_b.search_active_ratio < 0.25:
        consumption_mode = "편향형"
    elif layer_b.search_active_ratio >= 0.3 and layer_b.exploration_depth >= 0.45:
        consumption_mode = "탐색형"
    elif layer_b.viewing_concentration >= 0.55 and layer_b.exploration_depth < 0.35:
        consumption_mode = "습관형"
    else:
        consumption_mode = "균형형"

    gaps = {
        "search_active_ratio": max(0.0, 0.35 - layer_b.search_active_ratio),
        "viewing_concentration": max(0.0, layer_b.viewing_concentration - 0.45),
        "taste_diversity_index": max(
            0.0, (55.0 - layer_b.taste_diversity_index) / 100
        ),
        "exploration_depth": max(0.0, 0.4 - layer_b.exploration_depth),
    }
    lever_key = max(gaps, key=gaps.get)
    primary_lever = (
        _LAYER_B_LABELS["search_active_ratio"]
        if gaps[lever_key] <= 0.0
        else _LAYER_B_LABELS[lever_key]
    )

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
        sovereignty_verdict = "개선 권장"
    elif risk >= 2:
        sovereignty_verdict = "주의"
    else:
        sovereignty_verdict = "양호"

    dominant = _top_axes(axes, 1)[0]
    dominant_label = _AXIS_LABELS.get(dominant, dominant)

    if axes.intellectual_curiosity >= 60 and layer_b.exploration_depth < 0.35:
        radar_gap_insight = (
            "지적 호기심 점수는 높지만 탐색 깊이가 낮아 "
            "새 주제를 얕게 훑는 패턴이 보입니다."
        )
    elif axes.social_awareness >= 65 and layer_b.viewing_concentration >= 0.7:
        radar_gap_insight = (
            "사회·시선 관심은 넓으나 채널 편중도가 높아 시청 출처가 좁습니다."
        )
    elif axes.depth_immersion >= 70 and layer_b.exploration_depth < 0.4:
        radar_gap_insight = (
            "평소 몰입 성향은 강하지만 검색 기반 탐색 깊이는 상대적으로 낮습니다."
        )
    elif layer_b.taste_diversity_index < 40:
        radar_gap_insight = (
            f"취향 다양성이 낮고 {dominant_label} 축이 두드러져 "
            "특정 영역에 쏠려 있습니다."
        )
    else:
        weak_key = min(SYNAPSE_AXIS_KEYS, key=lambda key: getattr(axes, key))
        weak_label = _AXIS_LABELS.get(weak_key, weak_key)
        radar_gap_insight = (
            f"레이더 상위 축({dominant_label})과 "
            f"보완 축({weak_label}) 사이 균형을 보며 "
            "소비 패턴을 조정할 여지가 있습니다."
        )

    return ProfileInterpretation(
        consumption_mode=consumption_mode,
        primary_lever=primary_lever,
        sovereignty_verdict=sovereignty_verdict,
        radar_gap_insight=radar_gap_insight,
    )


def interpretation_node(state: ProfilerState) -> dict:
    interpretation = _compute_interpretation(state["axes"], state["layer_b"])
    log = list(state.get("investigation_log", []))
    log.append(f"interpretation: mode={interpretation.consumption_mode}")
    log.append(f"interpretation: lever={interpretation.primary_lever}")
    log.append(f"interpretation: verdict={interpretation.sovereignty_verdict}")
    return {
        "interpretation": interpretation,
        "current_step": "interpretation",
        "investigation_log": log,
    }
