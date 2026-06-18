"""Archiver LangGraph 워크플로우 — 자율 판단 루프형 에이전트."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from app.agents.archiver.branches import (
    route_after_collect,
    route_after_evaluator,
    route_after_router,
)
from app.agents.archiver.steps import classify, collect, evaluate, respond, search
from app.agents.archiver.store import ArchiverStore, build_run_config
from app.agents.archiver.trace import log_workflow_end, log_workflow_start
from app.agents.archiver.types import (
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    ArchiverState,
    ArchiverStreamEvent,
)

_compiled_graph = None
_archiver_engine_runner: ArchiverEngine | None = None


def build_archiver_engine():
    """router → (GENERAL⇒respond | RAG/BASIC⇒collect | SEARCH⇒search) ⇄ evaluator → respond."""
    graph = StateGraph(ArchiverState)

    graph.add_node("router", classify)
    graph.add_node("collect", collect)
    graph.add_node("search", search)
    graph.add_node("evaluator", evaluate)
    graph.add_node("respond", respond)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "respond": "respond",
            "collect": "collect",
            "search": "search",
        },
    )
    graph.add_conditional_edges(
        "collect",
        route_after_collect,
        {"evaluator": "evaluator"},
    )
    graph.add_edge("search", "evaluator")
    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "search": "search",
            "collect": "collect",
            "respond": "respond",
        },
    )
    graph.add_edge("respond", END)

    return graph.compile()


def _get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_archiver_engine()
    return _compiled_graph


class ArchiverEngine:
    """LangGraph 엔진 래퍼 — custom stream을 ArchiverStreamEvent로 정규화한다."""

    def __init__(self) -> None:
        self._graph = _get_compiled_graph()

    @staticmethod
    def build_initial_state(
        *,
        message: str,
        user_id: int,
        session_id: str,
        context_title: str | None = None,
        context_url: str | None = None,
    ) -> ArchiverState:
        """Service가 주입하는 초기 State 가방."""
        return {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "session_id": session_id,
            "context_title": context_title or NO_CONTEXT_TITLE,
            "context_url": context_url or NO_CONTEXT_URL,
            "retrieval_attempts": 0,
            "search_attempts": 0,
        }

    async def stream(
        self,
        *,
        initial_state: ArchiverState,
        store: ArchiverStore | None = None,
    ) -> AsyncIterator[ArchiverStreamEvent]:
        """LangGraph 루프 실행 — store는 RAG 수집 Port."""
        run_config = build_run_config(store=store)
        log_workflow_start(state=initial_state)
        started_at = time.perf_counter()

        final_state: dict[str, Any] = dict(initial_state)

        async for mode, chunk in self._graph.astream(
            initial_state,
            config=run_config,
            stream_mode=["custom", "values"],
        ):
            if mode == "values" and isinstance(chunk, dict):
                final_state = chunk
                continue

            if mode != "custom" or not isinstance(chunk, dict):
                continue

            event_type = chunk.get("event")
            content = chunk.get("content")
            if not content or event_type not in {"status", "token"}:
                continue

            yield ArchiverStreamEvent(event=event_type, content=content)

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        log_workflow_end(final_state, latency_ms=latency_ms)


def get_archiver_engine() -> ArchiverEngine:
    """FastAPI Depends용 ArchiverEngine 싱글톤."""
    global _archiver_engine_runner
    if _archiver_engine_runner is None:
        _archiver_engine_runner = ArchiverEngine()
    return _archiver_engine_runner


# 하위 호환 alias
ArchiverGraph = ArchiverEngine
get_archiver_graph = get_archiver_engine
