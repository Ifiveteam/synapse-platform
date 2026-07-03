"""evaluate 노드 — 자기판단(규칙): 근거·커버리지 보고 retrieve/generate/done 결정."""

from __future__ import annotations

from typing import Any

from app.agents.navigator.sub_agent.guide.constants import (
    MAX_GEN_ATTEMPTS,
    MAX_RETRIEVE_ATTEMPTS,
)
from app.agents.navigator.sub_agent.guide.state import GuideState


async def evaluate(state: GuideState) -> dict[str, Any]:
    draft = state.get("draft")
    deepen = state["deepen_targets"]
    expand = state["expand_domains"]
    evidence = state.get("evidence") or {}
    retrieve_attempts = state.get("retrieve_attempts", 0)
    gen_attempts = state.get("gen_attempts", 0)

    # 생성 실패 → 한도 내면 재생성, 아니면 종료(폴백)
    if draft is None:
        if gen_attempts < MAX_GEN_ATTEMPTS:
            return {"decision": "generate"}
        return {"decision": "done", "result": None}

    covered = {step.axis for step in draft.steps}
    coverage_ok = all(t in covered for t in (*deepen, *expand))
    # 근거는 심화(성향)만 필요 — 확장은 원래 근거가 없을 수 있음
    grounding_missing = any(not evidence.get(a) for a in deepen)

    # 심화 근거 부족 → 재검색(완화)
    if deepen and grounding_missing and retrieve_attempts < MAX_RETRIEVE_ATTEMPTS:
        return {"decision": "retrieve"}
    # 커버 부족 → 재생성
    if not coverage_ok and gen_attempts < MAX_GEN_ATTEMPTS:
        return {"decision": "generate"}

    return {"decision": "done", "result": draft}
