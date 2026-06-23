"""Navigator 이상향 기능 — 추출·보정·제안·비교 (코드가 부르는 기능).

LLM이 호출하는 도구(function-calling)는 `tools/`에 둔다. 여기는 코드가 부르는 함수.
"""

from __future__ import annotations

import asyncio

from app.agents.navigator.behavior_map import derive_8_from_13
from app.agents.navigator.constants import (
    AXIS_MAX,
    AXIS_MIN,
    BEHAVIOR_AXES,
    PROPOSE_TEMPERATURE,
    VALUES_TEMPERAMENT_AXES,
)
from app.agents.navigator.gemini import invoke_structured
from app.agents.navigator.prompts.propose import build_propose_prompt
from app.agents.navigator.schemas import (
    AxisGap,
    IdealType,
    IdealValuesDesign,
    ProposedIdeal,
    RadarComparison,
)
from app.agents.profiler.axis_labels import SCORE_LABELS_KO


def clamp_value(value: float) -> float:
    return max(AXIS_MIN, min(AXIS_MAX, float(value)))


def clamp_scores(scores: dict[str, float]) -> dict[str, float]:
    return {axis: clamp_value(scores.get(axis, 0.0)) for axis in BEHAVIOR_AXES}


def clamp_values_13(values: dict[str, float]) -> dict[str, float]:
    return {
        axis: clamp_value(values.get(axis, 0.0)) for axis in VALUES_TEMPERAMENT_AXES
    }


def extract_8axis(profile_21: dict[str, float]) -> dict[str, float]:
    """21축 dict에서 행동 8축만 추출 (없으면 0.0)."""
    return {axis: float(profile_21.get(axis, 0.0)) for axis in BEHAVIOR_AXES}


# 페르소나 폴백 — LLM 명칭이 없을 때(챗 맞춤 확정 등) 상위 축으로 생성.
_PERSONA_ADJ: dict[str, str] = {
    "exploration": "호기심 많은",
    "analytical": "분석적인",
    "creativity": "창의적인",
    "execution": "실행하는",
    "achievement_drive": "성취 지향",
    "autonomy": "자기주도적인",
    "sociality": "사교적인",
    "sensitivity": "감수성 높은",
}
_PERSONA_NOUN: dict[str, str] = {
    "exploration": "탐색가",
    "analytical": "분석가",
    "creativity": "창작 소비자",
    "execution": "실천가",
    "achievement_drive": "성장 추구자",
    "autonomy": "큐레이터",
    "sociality": "관람자",
    "sensitivity": "감성 소비자",
}


def persona_label_from_scores(scores8: dict[str, float]) -> str:
    """상위 행동 축 기반 규칙형 페르소나 명칭 (LLM 명칭 폴백)."""
    if not scores8:
        return "균형형 소비자"
    top = max(BEHAVIOR_AXES, key=lambda a: float(scores8.get(a, 0.0)))
    return f"{_PERSONA_ADJ.get(top, '균형적인')} {_PERSONA_NOUN.get(top, '소비자')}"


async def _propose_one(
    ideal_type: IdealType,
    profile_21: dict[str, float],
    top_interests: dict[str, list] | None,
) -> ProposedIdeal:
    """LLM이 이상향 13축을 설계 → 8축을 파생해 ProposedIdeal로 묶는다."""
    design = await invoke_structured(
        system_instruction=build_propose_prompt(ideal_type, profile_21, top_interests),
        user_content="이 사용자에게 맞는 이상향을 설계하세요.",
        schema=IdealValuesDesign,
        temperature=PROPOSE_TEMPERATURE,
    )
    values13 = clamp_values_13(design.values())
    scores8 = derive_8_from_13(values13)
    return ProposedIdeal(
        ideal_type=ideal_type,
        scores8=scores8,
        values13=values13,
        persona_label=design.persona_label,
        reasoning=design.reasoning,
    )


_PROPOSAL_TYPES: tuple[IdealType, ...] = (
    IdealType.OPPOSITE,
    IdealType.DEEPEN,
    IdealType.BALANCE,
)


async def propose_ideals(
    profile_21: dict[str, float],
    top_interests: dict[str, list] | None = None,
) -> list[ProposedIdeal]:
    """이상향 3종(반대·강점심화·균형)을 동시에 생성한다 (각 13축 설계 + 8축 파생)."""
    return list(
        await asyncio.gather(
            *(
                _propose_one(ideal_type, profile_21, top_interests)
                for ideal_type in _PROPOSAL_TYPES
            )
        )
    )


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
