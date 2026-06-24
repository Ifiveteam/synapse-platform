"""Archiver ??? ??? ??? ? Mock LLM?? 4?? + evaluator ??? ??."""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any
from unittest.mock import patch

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from app.agents.archiver.engine import ArchiverEngine, build_archiver_engine
from app.agents.archiver.models import COLLECT_NODE, RAG_NODE, SEARCH_NODE
from app.agents.archiver.core.store import PastKnowledgeHit
from app.agents.archiver.models import ArchiverRoute, Evaluation


class _FakeStore:
    async def search_past_knowledge(self, *args: Any, **kwargs: Any) -> list[PastKnowledgeHit]:
        return [
            PastKnowledgeHit(
                role="user",
                content="??? ??? React ? ?? ??",
                context_title="React docs",
                created_at="2026-06-01",
            )
        ]


async def _mock_respond(state: dict[str, Any]) -> dict[str, Any]:
    writer = get_stream_writer()
    writer({"event": "status", "content": "[mock] respond status\n\n"})
    writer({"event": "token", "content": "mock-answer"})
    return {"final_response": "mock-answer", "current_step": "respond"}


def _route_targets(route: ArchiverRoute) -> list[str]:
    if route == ArchiverRoute.GENERAL:
        return []
    if route == ArchiverRoute.RAG:
        return [RAG_NODE]
    if route == ArchiverRoute.SEARCH:
        return [SEARCH_NODE]
    if route == ArchiverRoute.BASIC:
        return [COLLECT_NODE]
    return []


def _mock_classify(route: ArchiverRoute) -> Any:
    async def _fn(state: dict[str, Any]) -> dict[str, Any]:
        writer = get_stream_writer()
        if route == ArchiverRoute.GENERAL:
            writer(
                {
                    "event": "status",
                    "content": "?? [Router] `GENERAL` ?? ?? ? ????? ??? ???? ??? ?????...\n\n",
                }
            )
            return {
                "route": route,
                "is_general": True,
                "target_engines": [],
                "current_step": "router",
            }

        writer(
            {
                "event": "status",
                "content": f"?? [Router] ?? ??? `{route.value}`(?)? ??????...\n\n",
            }
        )
        return {
            "route": route,
            "is_general": False,
            "target_engines": _route_targets(route),
            "current_step": "router",
        }

    return _fn


def _safe_repr(text: str) -> str:
    return repr(text).encode("ascii", "backslashreplace").decode("ascii")


async def _run_path(
    *,
    label: str,
    route: ArchiverRoute,
    extra_patches: dict[str, Any] | None = None,
    state_overrides: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    engine = ArchiverEngine()
    state = ArchiverEngine.build_initial_state(
        messages=[HumanMessage(content="smoke test")],
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        session_id="smoke-session",
    )
    if state_overrides:
        state.update(state_overrides)
    patches: dict[str, Any] = {
        "app.agents.archiver.workflow.classify": _mock_classify(route),
        "app.agents.archiver.workflow.respond": _mock_respond,
    }
    if extra_patches:
        patches.update(extra_patches)

    statuses: list[str] = []
    tokens: list[str] = []

    patchers = [patch(target, new=mock) for target, mock in patches.items()]
    for p in patchers:
        p.start()
    try:
        # graph singleton? steps? import ??? ?????? ?? ??? ????? ????
        import app.agents.archiver.engine as engine_mod

        engine_mod._compiled_graph = build_archiver_engine()
        engine._graph = engine_mod._compiled_graph

        async for event in engine.stream(initial_state=state, store=_FakeStore()):
            if event.event == "status":
                statuses.append(event.content)
            elif event.event == "token":
                tokens.append(event.content)
    finally:
        for p in patchers:
            p.stop()

    print(f"[{label}] status={len(statuses)} token={_safe_repr(''.join(tokens))}")
    return statuses, tokens


async def main() -> int:
    errors: list[str] = []

    # GENERAL fast-path
    st, tk = await _run_path(label="GENERAL", route=ArchiverRoute.GENERAL)
    if not tk or tk[0] != "mock-answer":
        errors.append("GENERAL: token missing")
    if not any("GENERAL" in s for s in st):
        errors.append("GENERAL: router status missing")

    # RAG ? rag_node ? evaluator(sufficient) ? respond
    async def _mock_eval_sufficient(state: dict[str, Any]) -> dict[str, Any]:
        ev = Evaluation(
            is_sufficient=True,
            reason="RAG ??",
            recommended_action="none",
            dom_verdict="not_run",
            rag_verdict="sufficient",
            search_verdict="not_run",
        )
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] evaluator ok\n\n"})
        return {"evaluation_result": ev.to_state_dict(), "current_step": "evaluator"}

    async def _mock_rag_node(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] rag_node\n\n"})
        return {
            "context_rag": "past knowledge",
            "rag_data": "past knowledge",
            "retrieval_attempts": 1,
            "current_step": RAG_NODE,
            "executed_steps": [RAG_NODE],
        }

    st, tk = await _run_path(
        label="RAG",
        route=ArchiverRoute.RAG,
        extra_patches={
            "app.agents.archiver.workflow.rag_node": _mock_rag_node,
            "app.agents.archiver.workflow.evaluate": _mock_eval_sufficient,
        },
    )
    if not tk:
        errors.append("RAG: token missing")

    # SEARCH -> search_node -> evaluator(sufficient) -> respond
    search_calls = {"n": 0}

    async def _mock_search_node(state: dict[str, Any]) -> dict[str, Any]:
        search_calls["n"] += 1
        writer = get_stream_writer()
        writer({"event": "status", "content": f"[mock] search #{search_calls['n']}\n\n"})
        return {
            "context_search": f"result-{search_calls['n']}",
            "search_data": f"result-{search_calls['n']}",
            "search_attempts": search_calls["n"],
            "current_step": SEARCH_NODE,
            "executed_steps": [SEARCH_NODE],
        }

    st, tk = await _run_path(
        label="SEARCH",
        route=ArchiverRoute.SEARCH,
        extra_patches={
            "app.agents.archiver.workflow.search_node": _mock_search_node,
            "app.agents.archiver.workflow.evaluate": _mock_eval_sufficient,
        },
    )
    if search_calls["n"] < 1:
        errors.append(f"SEARCH: expected 1 search call, got {search_calls['n']}")
    if not tk:
        errors.append("SEARCH: token missing")

    # BASIC path
    async def _mock_collect_node(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] collect_node\n\n"})
        return {
            "context_body": "page body",
            "context_dom": "page body",
            "current_step": COLLECT_NODE,
            "executed_steps": [COLLECT_NODE],
        }

    st, tk = await _run_path(
        label="BASIC",
        route=ArchiverRoute.BASIC,
        extra_patches={
            "app.agents.archiver.workflow.collect_node": _mock_collect_node,
            "app.agents.archiver.workflow.evaluate": _mock_eval_sufficient,
        },
        state_overrides={
            "context_body": (
                "This is a sufficiently long page body for the BASIC smoke path. "
                "It contains enough natural language text to pass context quality checks."
            ),
            "context_dom": (
                "This is a sufficiently long page body for the BASIC smoke path. "
                "It contains enough natural language text to pass context quality checks."
            ),
        },
    )
    if not tk:
        errors.append("BASIC: token missing")

    if errors:
        print("\n[FAIL]")
        for e in errors:
            print(" -", e)
        return 1

    print("\n[PASS] all archiver runtime smoke paths")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
