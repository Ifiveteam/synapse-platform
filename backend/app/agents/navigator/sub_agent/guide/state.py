"""가이드 서브에이전트 LangGraph 상태 (심화·확장 두 갈래)."""

from __future__ import annotations

import uuid
from typing import NotRequired, TypedDict

from app.agents.navigator.schemas import Guide
from app.agents.navigator.sub_agent.guide.schemas import CatalogHit


class GuideState(TypedDict):
    user_id: uuid.UUID
    ideal_type: str
    reasoning: str

    # 심화(성향 갭) / 확장(도메인 상향) 타깃
    deepen_targets: list[str]  # 성향키 (immersion 등)
    deepen_gaps: dict[str, float]
    expand_domains: list[str]  # 도메인명 (지식·교육 등)
    expand_gaps: dict[str, float]

    # 근거: 심화=성향키→실시청, 확장=도메인→다리(임계값 통과분)
    evidence: NotRequired[dict[str, list[CatalogHit]]]
    bridge_evidence: NotRequired[dict[str, list[CatalogHit]]]

    draft: NotRequired[Guide | None]
    retrieve_attempts: NotRequired[int]
    gen_attempts: NotRequired[int]
    relax_level: NotRequired[int]
    decision: NotRequired[str]
    result: NotRequired[Guide | None]
