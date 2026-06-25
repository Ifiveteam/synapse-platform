"""Navigator 이상향 제안 — LLM이 13축(가치관10+기질3)을 설계하고 8축을 파생한다.

축 규칙(추출·보정·비교·페르소나)은 axes.py, 13축 → 8축 파생은 behavior_map.py.
"""

from __future__ import annotations

import asyncio

from app.agents.navigator.axes import clamp_values_13
from app.agents.navigator.behavior_map import derive_8_from_13
from app.agents.navigator.constants import PROPOSE_TEMPERATURE
from app.agents.navigator.llm import invoke_structured
from app.agents.navigator.prompts.propose import build_propose_prompt
from app.agents.navigator.schemas import (
    IdealType,
    IdealValuesDesign,
    ProposedIdeal,
)


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
