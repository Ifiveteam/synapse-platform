"""generate 노드 — 근거(있으면)로 가이드 생성, 없으면 폴백."""

from __future__ import annotations

from typing import Any

from app.agents.navigator.gemini import invoke_structured_safe
from app.agents.navigator.schemas import Guide
from app.agents.navigator.sub_agent.guide.prompts import (
    build_fallback_prompt,
    build_grounded_prompt,
)
from app.agents.navigator.sub_agent.guide.state import GuideState
from app.agents.profiler.axis_labels import SCORE_LABELS_KO

_GEN_TEMPERATURE = 0.5


async def generate(state: GuideState) -> dict[str, Any]:
    weak_axes = state["weak_axes"]
    gap_by_axis = state["gap_by_axis"]
    evidence = state.get("evidence") or {}
    has_evidence = any(evidence.get(axis) for axis in weak_axes)

    if has_evidence:
        system = build_grounded_prompt(
            weak_axes=weak_axes,
            gap_by_axis=gap_by_axis,
            evidence=evidence,
            ideal_type=state["ideal_type"],
            reasoning=state["reasoning"],
        )
    else:
        system = build_fallback_prompt(
            weak_axes=weak_axes,
            gap_by_axis=gap_by_axis,
            ideal_type=state["ideal_type"],
            reasoning=state["reasoning"],
        )

    guide = await invoke_structured_safe(
        system_instruction=system,
        user_content="이상향 달성을 위한 행동 가이드를 작성하세요.",
        schema=Guide,
        temperature=_GEN_TEMPERATURE,
    )

    if guide is not None:
        for step in guide.steps:
            if not step.label_ko:
                step.label_ko = SCORE_LABELS_KO.get(step.axis, step.axis)

    return {"draft": guide, "gen_attempts": state.get("gen_attempts", 0) + 1}
