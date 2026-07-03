"""generate 노드 — 심화(근거)·확장(다리/전방향) 가이드 생성 + kind/label 정규화."""

from __future__ import annotations

from typing import Any

from app.agents.navigator.constants import (
    DISPOSITION_AXES,
    DISPOSITION_LABELS_KO,
    INTEREST_DOMAINS,
)
from app.agents.navigator.llm import invoke_structured_safe
from app.agents.navigator.schemas import Guide
from app.agents.navigator.sub_agent.guide.prompts import build_guide_prompt
from app.agents.navigator.sub_agent.guide.state import GuideState

_GEN_TEMPERATURE = 0.5


def _normalize(guide: Guide) -> Guide:
    """axis로 kind·label_ko를 확정한다 (LLM 오분류 보정)."""
    for step in guide.steps:
        if step.axis in DISPOSITION_AXES:
            step.kind = "deepen"
            step.label_ko = DISPOSITION_LABELS_KO.get(step.axis, step.axis)
        elif step.axis in INTEREST_DOMAINS:
            step.kind = "expand"
            step.label_ko = step.axis
        elif not step.label_ko:
            step.label_ko = step.axis
    return guide


async def generate(state: GuideState) -> dict[str, Any]:
    system = build_guide_prompt(
        deepen_targets=state["deepen_targets"],
        deepen_gaps=state["deepen_gaps"],
        evidence=state.get("evidence") or {},
        expand_domains=state["expand_domains"],
        expand_gaps=state["expand_gaps"],
        bridge_evidence=state.get("bridge_evidence") or {},
        ideal_type=state["ideal_type"],
        reasoning=state["reasoning"],
    )

    guide = await invoke_structured_safe(
        system_instruction=system,
        user_content="이상향 달성을 위한 심화·확장 행동 가이드를 작성하세요.",
        schema=Guide,
        temperature=_GEN_TEMPERATURE,
    )
    if guide is not None:
        guide = _normalize(guide)

    return {"draft": guide, "gen_attempts": state.get("gen_attempts", 0) + 1}
