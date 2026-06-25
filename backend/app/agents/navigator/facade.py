"""Navigator 에이전트 파사드 — LLM 서브에이전트(propose·guide·youtube)와 챗 그래프를
한 문으로 묶는 진입점.

DB·HTTP는 모른다. plain 데이터(dict)를 받고 도메인 객체를 반환한다.
규칙 계산(extract_8axis·derive_8_from_13·compare 등)은 파사드를 거치지 않고
service가 ideal·behavior_map을 직접 호출한다 — 파사드는 LLM/그래프 위임만 담당.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage

from app.agents.navigator.graph import build_navigator_graph
from app.agents.navigator.ideal import propose_ideals
from app.agents.navigator.schemas import (
    Guide,
    NavigatorStreamEvent,
    PlaylistItem,
    ProposedIdeal,
)
from app.agents.navigator.state import NavigatorState
from app.agents.navigator.sub_agent.guide import CatalogStore, run_guide
from app.agents.navigator.sub_agent.youtube import (
    PlaylistBuild,
    PlaylistStore,
    RefreshResult,
    run_playlist,
)
from app.agents.navigator.sub_agent.youtube import (
    edit_playlist as _edit_playlist,
)
from app.agents.navigator.sub_agent.youtube import (
    refresh_item as _refresh_item,
)

_ALLOWED_EVENTS = {"status", "token", "ideal"}


class NavigatorAgent:
    """LLM 서브에이전트(propose·guide·youtube)와 챗 그래프를 묶어 노출하는 파사드."""

    def __init__(self) -> None:
        self._graph = build_navigator_graph()

    # ── 단발성 LLM 능력 (서브에이전트 위임) ──────────────────
    async def propose(
        self,
        profile_21: dict[str, float],
        top_interests: dict[str, list] | None = None,
    ) -> list[ProposedIdeal]:
        """21축 → 반대·강점심화·균형 이상향 3종 (각 13축 설계 + 8축 파생)."""
        return await propose_ideals(profile_21, top_interests)

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

    async def generate_playlist(
        self,
        *,
        store: PlaylistStore | None,
        user_id: uuid.UUID,
        persona_label: str,
        values13: dict[str, float],
        ideal_type: str,
        reasoning: str,
    ) -> PlaylistBuild:
        """YouTube 재생목록 서브에이전트에 위임 — 채널 발굴→RSS→큐레이션."""
        return await run_playlist(
            store=store,
            user_id=user_id,
            persona_label=persona_label,
            values13=values13,
            ideal_type=ideal_type,
            reasoning=reasoning,
        )

    async def refresh_item(
        self,
        *,
        store: PlaylistStore | None,
        user_id: uuid.UUID,
        items: list[PlaylistItem],
        reservoir: list[PlaylistItem],
        channel_ids: list[str],
        target_video_id: str,
    ) -> RefreshResult:
        """재생목록 영상 1개 교체 (저수지 → 채널 re-RSS)."""
        return await _refresh_item(
            store=store,
            user_id=user_id,
            items=items,
            reservoir=reservoir,
            channel_ids=channel_ids,
            target_video_id=target_video_id,
        )

    def edit_playlist(
        self,
        *,
        store: PlaylistStore | None,
        user_id: uuid.UUID,
        items: list[PlaylistItem],
        reservoir: list[PlaylistItem],
        channels: list[dict],
        message: str,
    ) -> AsyncIterator[NavigatorStreamEvent]:
        """채팅으로 재생목록 부분수정 (status + 최종 playlist 이벤트 스트림)."""
        return _edit_playlist(
            store=store,
            user_id=user_id,
            items=items,
            reservoir=reservoir,
            channels=channels,
            message=message,
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
