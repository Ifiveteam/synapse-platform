"""Curator LangGraph 워크플로우."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.steps import classify, respond, retrieve
from app.agents.curator.types import (
    CuratorRoute,
    CuratorState,
    CuratorStreamEvent,
)


def _route_after_classify(state: CuratorState) -> str:
    if state.get("route") == CuratorRoute.MY_DATA:
        return "retrieve"
    return "respond"


def build_graph(db: AsyncSession):
    """db 세션을 inject해서 그래프를 빌드한다."""

    async def _retrieve(state: CuratorState) -> dict[str, Any]:
        return await retrieve(state, db)

    graph = StateGraph(CuratorState)

    graph.add_node("classify", classify)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("respond", respond)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        _route_after_classify,
        {"retrieve": "retrieve", "respond": "respond"},
    )
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


class CuratorEngine:
    @staticmethod
    def build_initial_state(
        *,
        messages: list[BaseMessage],
        user_id: uuid.UUID,
        session_id: str,
    ) -> CuratorState:
        return {
            "messages": messages,
            "user_id": user_id,
            "session_id": session_id,
        }

    async def stream(
        self,
        *,
        initial_state: CuratorState,
        db: AsyncSession,
    ) -> AsyncIterator[CuratorStreamEvent]:
        graph = build_graph(db)

        async for mode, chunk in graph.astream(
            initial_state,
            stream_mode=["custom", "values"],
        ):
            if mode != "custom" or not isinstance(chunk, dict):
                continue

            event_type = chunk.get("event")
            content = chunk.get("content")
            if not content or event_type not in {"status", "token", "chart"}:
                continue

            yield CuratorStreamEvent(event=event_type, content=content)


_engine: CuratorEngine | None = None


def get_curator_engine() -> CuratorEngine:
    global _engine
    if _engine is None:
        _engine = CuratorEngine()
    return _engine
