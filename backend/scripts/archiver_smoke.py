"""Archiver 런타임 스모크 테스트 — Mock LLM으로 4경로 + evaluator 역주행 검증."""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any
from unittest.mock import patch

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from app.agents.archiver.engine import ArchiverEngine, build_archiver_engine
from app.agents.archiver.store import PastKnowledgeHit
from app.agents.archiver.types import ArchiverRoute, Evaluation


class _FakeStore:
    async def search_past_knowledge(self, *args: Any, **kwargs: Any) -> list[PastKnowledgeHit]:
        return [
            PastKnowledgeHit(
                role="user",
                content="예전에 저장한 React 훅 정리 노트",
                context_title="React docs",
                created_at="2026-06-01",
            )
        ]


async def _mock_respond(state: dict[str, Any]) -> dict[str, Any]:
    writer = get_stream_writer()
    writer({"event": "status", "content": "[mock] respond status\n\n"})
    writer({"event": "token", "content": "mock-answer"})
    return {"final_response": "mock-answer", "current_step": "respond"}


def _mock_classify(route: ArchiverRoute) -> Any:
    async def _fn(state: dict[str, Any]) -> dict[str, Any]:
        writer = get_stream_writer()
        if route == ArchiverRoute.GENERAL:
            writer(
                {
                    "event": "status",
                    "content": "💬 [Router] `GENERAL` 일상 대화 — 수집·평가 단계를 건너뛰고 답변을 생성합니다...\n\n",
                }
            )
        else:
            writer(
                {
                    "event": "status",
                    "content": f"🔀 [Router] 처리 경로를 `{route.value}`(으)로 분류했습니다...\n\n",
                }
            )
        return {"route": route, "current_step": "router"}

    return _fn


async def _run_path(
    *,
    label: str,
    route: ArchiverRoute,
    extra_patches: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    engine = ArchiverEngine()
    state = ArchiverEngine.build_initial_state(
        messages=[HumanMessage(content="smoke test")],
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        session_id="smoke-session",
    )
    patches: dict[str, Any] = {
        "app.agents.archiver.engine.classify": _mock_classify(route),
        "app.agents.archiver.engine.respond": _mock_respond,
    }
    if extra_patches:
        patches.update(extra_patches)

    statuses: list[str] = []
    tokens: list[str] = []

    patchers = [patch(target, new=mock) for target, mock in patches.items()]
    for p in patchers:
        p.start()
    try:
        # graph singleton은 steps를 import 시점에 바인딩하므로 노드 패치가 적용되도록 재컴파일
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

    print(f"[{label}] status={len(statuses)} token={''.join(tokens)!r}")
    return statuses, tokens


async def main() -> int:
    errors: list[str] = []

    # GENERAL fast-path
    st, tk = await _run_path(label="GENERAL", route=ArchiverRoute.GENERAL)
    if not tk or tk[0] != "mock-answer":
        errors.append("GENERAL: token missing")
    if not any("GENERAL" in s or "일상" in s for s in st):
        errors.append("GENERAL: router status missing")

    # RAG → collect → evaluator(sufficient) → respond
    async def _mock_eval_sufficient(state: dict[str, Any]) -> dict[str, Any]:
        ev = Evaluation(
            is_sufficient=True,
            score=85,
            reason="RAG 충분",
            recommended_action="respond",
        )
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] evaluator ok\n\n"})
        return {"evaluation_result": ev.to_state_dict(), "current_step": "evaluator"}

    async def _mock_collect_rag(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] collect rag\n\n"})
        return {
            "rag_data": "past knowledge",
            "retrieval_attempts": 1,
            "current_step": "collect",
        }

    st, tk = await _run_path(
        label="RAG",
        route=ArchiverRoute.RAG,
        extra_patches={
            "app.agents.archiver.engine.collect": _mock_collect_rag,
            "app.agents.archiver.engine.evaluate": _mock_eval_sufficient,
        },
    )
    if not tk:
        errors.append("RAG: token missing")

    # SEARCH → evaluator loop → search 역주행 → respond
    eval_calls = {"n": 0}

    async def _mock_eval_loop(state: dict[str, Any]) -> dict[str, Any]:
        eval_calls["n"] += 1
        if eval_calls["n"] == 1:
            ev = Evaluation(
                is_sufficient=False,
                score=20,
                reason="검색 부족",
                recommended_action="search",
            )
        else:
            ev = Evaluation(
                is_sufficient=True,
                score=80,
                reason="재검색 충분",
                recommended_action="respond",
            )
        writer = get_stream_writer()
        writer({"event": "status", "content": f"[mock] eval #{eval_calls['n']}\n\n"})
        return {"evaluation_result": ev.to_state_dict(), "current_step": "evaluator"}

    search_calls = {"n": 0}

    async def _mock_search(state: dict[str, Any]) -> dict[str, Any]:
        search_calls["n"] += 1
        writer = get_stream_writer()
        writer({"event": "status", "content": f"[mock] search #{search_calls['n']}\n\n"})
        return {
            "search_data": f"result-{search_calls['n']}",
            "search_attempts": search_calls["n"],
            "current_step": "search",
        }

    st, tk = await _run_path(
        label="SEARCH+loop",
        route=ArchiverRoute.SEARCH,
        extra_patches={
            "app.agents.archiver.engine.search": _mock_search,
            "app.agents.archiver.engine.evaluate": _mock_eval_loop,
        },
    )
    if search_calls["n"] < 2:
        errors.append(f"SEARCH loop: expected 2 search calls, got {search_calls['n']}")
    if eval_calls["n"] < 2:
        errors.append(f"SEARCH loop: expected 2 eval calls, got {eval_calls['n']}")

    # BASIC path
    async def _mock_collect_basic(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] collect basic\n\n"})
        return {"context_body": "page body", "current_step": "collect"}

    st, tk = await _run_path(
        label="BASIC",
        route=ArchiverRoute.BASIC,
        extra_patches={
            "app.agents.archiver.engine.collect": _mock_collect_basic,
            "app.agents.archiver.engine.evaluate": _mock_eval_sufficient,
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
