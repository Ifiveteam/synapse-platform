"""Navigator 에이전트 파사드 — 기능(ideal·guide)·graph 조율을 소유하는 진입점.

DB·HTTP는 모른다. plain 데이터(dict)를 받고 도메인 객체를 반환한다.
service는 이 파사드만 호출하고, ideal·guide·graph를 직접 import하지 않는다.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage

from app.agents.navigator.behavior_map import derive_8_from_13
from app.agents.navigator.graph import build_navigator_graph
from app.agents.navigator.ideal import (
    clamp_scores,
    extract_8axis,
    persona_label_from_scores,
    propose_ideals,
)
from app.agents.navigator.ideal import (
    compare as compute_comparison,
)
from app.agents.navigator.schemas import (
    Guide,
    NavigatorStreamEvent,
    ProposedIdeal,
    RadarComparison,
)
from app.agents.navigator.state import NavigatorState
from app.agents.navigator.sub_agent.guide import CatalogStore, run_guide

_ALLOWED_EVENTS = {"status", "token", "ideal"}


class NavigatorAgent:
    """기능(ideal·guide)·graph(챗)를 조합해 에이전트 능력을 노출하는 파사드."""

    def __init__(self) -> None:
        self._graph = build_navigator_graph()

    # ── 단발성 능력 (tool 조합) ──────────────────────────────
    async def propose(
        self,
        profile_21: dict[str, float],
        top_interests: dict[str, list] | None = None,
    ) -> list[ProposedIdeal]:
        """21축 → 반대·강점심화·균형 이상향 3종 (각 13축 설계 + 8축 파생)."""
        return await propose_ideals(profile_21, top_interests)

    def current_axes(self, profile_21: dict[str, float]) -> dict[str, float]:
        """21축에서 행동 8축만 추출."""
        return extract_8axis(profile_21)

    def derive_behavior(self, values13: dict[str, float]) -> dict[str, float]:
        """이상향 13축 → 행동 8축 파생."""
        return derive_8_from_13(values13)

    def normalize_ideal(self, scores: dict[str, float]) -> dict[str, float]:
        """8축 점수를 0~100으로 보정."""
        return clamp_scores(scores)

    def persona_label(self, scores8: dict[str, float]) -> str:
        """상위 축 기반 규칙형 페르소나 명칭 (LLM 명칭 폴백용)."""
        return persona_label_from_scores(scores8)

    def compare(
        self, profile_21: dict[str, float], ideal_8: dict[str, float]
    ) -> RadarComparison:
        """현재(8축) vs 이상향 gap."""
        return compute_comparison(extract_8axis(profile_21), ideal_8)

    async def generate_guide(
        self,
        *,
        store: CatalogStore | None,
        user_id: uuid.UUID,
        profile_21: dict[str, float],
        ideal_8: dict[str, float],
        ideal_type: str,
        reasoning: str,
    ) -> Guide:
        """가이드 서브에이전트에 위임 — catalog RAG 근거로 행동 가이드 생성."""
        return await run_guide(
            store=store,
            user_id=user_id,
            profile_21=profile_21,
            ideal_8=ideal_8,
            ideal_type=ideal_type,
            reasoning=reasoning,
        )

    # ── 대화형 능력 (graph 실행) ─────────────────────────────
    async def chat_stream(
        self,
        *,
        messages: list[BaseMessage],
        user_id: uuid.UUID,
        session_id: str,
        profile_21: dict[str, float],
        current_8axis: dict[str, float],
        working_ideal: dict[str, float] | None = None,
        working_values: dict[str, float] | None = None,
        ideal_type: str | None = None,
        top_interests: dict[str, list] | None = None,
    ) -> AsyncIterator[NavigatorStreamEvent]:
        """챗 그래프를 돌려 custom 이벤트(status/token/ideal)만 방출한다."""
        initial_state = self._build_initial_state(
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            profile_21=profile_21,
            current_8axis=current_8axis,
            working_ideal=working_ideal,
            working_values=working_values,
            ideal_type=ideal_type,
            top_interests=top_interests,
        )
        async for mode, chunk in self._graph.astream(
            initial_state, stream_mode=["custom", "values"]
        ):
            if mode != "custom" or not isinstance(chunk, dict):
                continue
            event_type = chunk.get("event")
            content = chunk.get("content")
            if not content or event_type not in _ALLOWED_EVENTS:
                continue
            yield NavigatorStreamEvent(event=event_type, content=content)

    @staticmethod
    def _build_initial_state(
        *,
        messages: list[BaseMessage],
        user_id: uuid.UUID,
        session_id: str,
        profile_21: dict[str, float],
        current_8axis: dict[str, float],
        working_ideal: dict[str, float] | None = None,
        working_values: dict[str, float] | None = None,
        ideal_type: str | None = None,
        top_interests: dict[str, list] | None = None,
    ) -> NavigatorState:
        state: NavigatorState = {
            "messages": messages,
            "user_id": user_id,
            "session_id": session_id,
            "profile_21": profile_21,
            "current_8axis": current_8axis,
        }
        if working_ideal:
            state["working_ideal"] = working_ideal
        if working_values:
            state["working_values"] = working_values
        if ideal_type:
            state["ideal_type"] = ideal_type
        if top_interests:
            state["top_interests"] = top_interests
        return state


_navigator_agent: NavigatorAgent | None = None


def get_navigator_agent() -> NavigatorAgent:
    """FastAPI Depends용 NavigatorAgent 싱글톤."""
    global _navigator_agent
    if _navigator_agent is None:
        _navigator_agent = NavigatorAgent()
    return _navigator_agent
