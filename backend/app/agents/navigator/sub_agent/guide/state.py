"""가이드 서브에이전트 LangGraph 상태."""

from __future__ import annotations

import uuid
from typing import NotRequired, TypedDict

from app.agents.navigator.schemas import Guide
from app.agents.navigator.sub_agent.guide.schemas import CatalogHit


class GuideState(TypedDict):
    user_id: uuid.UUID
    profile_21: dict[str, float]
    ideal_8: dict[str, float]
    ideal_type: str
    reasoning: str

    weak_axes: list[str]
    gap_by_axis: dict[str, float]

    evidence: NotRequired[dict[str, list[CatalogHit]]]
    draft: NotRequired[Guide | None]
    retrieve_attempts: NotRequired[int]
    gen_attempts: NotRequired[int]
    relax_level: NotRequired[int]
    decision: NotRequired[str]
    result: NotRequired[Guide | None]
