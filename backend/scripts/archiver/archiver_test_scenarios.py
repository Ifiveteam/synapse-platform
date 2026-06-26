"""Archiver 시나리오 테스트 — 리팩터 후 회귀 방지용 최소 경로 검증."""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.types import Send

from app.agents.archiver.branches import needs_dom_collection, route_after_router
from app.agents.archiver.engine import ArchiverEngine, build_archiver_engine
from app.agents.archiver.models import COLLECT_NODE, RouterTargets, SEARCH_NODE
from app.agents.archiver.protocols.stream_status import MSG_ROUTER_GENERAL
from app.agents.archiver.steps.classify import _resolve_router_targets
from app.agents.archiver.steps.respond_context import resolve_system_instruction
from app.agents.archiver.utils.router_heuristics import needs_dialogue_context


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _long_dom_body() -> str:
    return (
        "This page explains the Synapse Archiver agent workflow in enough detail "
        "for dom collection quality checks to pass during scenario testing."
    )


def run_scenario_tests() -> list[str]:
    errors: list[str] = []

    # 1. 인사 → GENERAL, 수집 없음
    greeting_targets, greeting_detail, greeting_general = asyncio.run(
        _resolve_router_targets("안녕하세요")
    )
    _assert(
        greeting_targets == [] and greeting_general and greeting_detail == "preflight:greeting",
        "scenario1: greeting preflight -> GENERAL",
        errors,
    )
    _assert(
        route_after_router({"is_general": True, "target_engines": []}) == "respond",
        "scenario1: GENERAL fast-path skips collection",
        errors,
    )

    # 2. "이거 뭐야?" 1턴 + need_dom → 2차 dom_continuation
    turn1_state: dict[str, Any] = {
        "is_general": False,
        "target_engines": [COLLECT_NODE],
        "context_dom": "",
        "dom_continuation": False,
    }
    _assert(
        needs_dom_collection(turn1_state),
        "scenario2: turn1 missing dom -> needs_dom_collection",
        errors,
    )
    _assert(
        route_after_router(turn1_state) == "need_dom",
        "scenario2: turn1 routes to need_dom",
        errors,
    )

    turn2_state: dict[str, Any] = {
        "is_general": False,
        "target_engines": [COLLECT_NODE],
        "context_dom": _long_dom_body(),
        "dom_continuation": True,
    }
    _assert(
        not needs_dom_collection(turn2_state),
        "scenario2: dom_continuation skips need_dom gate",
        errors,
    )
    turn2_route = route_after_router(turn2_state)
    _assert(
        isinstance(turn2_route, list)
        and len(turn2_route) == 1
        and isinstance(turn2_route[0], Send)
        and turn2_route[0].node == COLLECT_NODE,
        "scenario2: turn2 fans out to collect_node",
        errors,
    )

    # 3. collect+search 병렬 → synthesis instruction에 dom+search 포함
    parallel_instruction, parallel_tools = resolve_system_instruction(
        {
            "is_general": False,
            "target_engines": [COLLECT_NODE, SEARCH_NODE],
            "context_title": "Synapse docs",
            "context_url": "https://example.com/archiver",
            "context_dom": "visible page excerpt",
            "context_search": "web search snippet",
        }
    )
    _assert(parallel_tools is None, "scenario3: parallel evidence skips search tool", errors)
    _assert(
        "visible page excerpt" in parallel_instruction
        and "web search snippet" in parallel_instruction,
        "scenario3: synthesis includes dom and search bodies",
        errors,
    )
    _assert(
        "[현재 페이지 본문]" in parallel_instruction
        and "[웹 검색 결과]" in parallel_instruction,
        "scenario3: synthesis includes dom and search section headers",
        errors,
    )

    # 4. 멀티턴 "이거 더 쉽게" → collect 없이 respond
    _assert(
        needs_dialogue_context("이거 더 쉽게"),
        "scenario4: follow-up needs dialogue context",
        errors,
    )
    _assert(
        route_after_router({"is_general": True, "target_engines": []}) == "respond",
        "scenario4: follow-up GENERAL routes directly to respond",
        errors,
    )

    return errors


async def _run_engine_scenarios(errors: list[str]) -> None:
    """dom_continuation 2턴·멀티턴 follow-up 런타임 시나리오."""

    async def _mock_respond(state: dict[str, Any]) -> dict[str, Any]:
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] respond\n\n"})
        writer({"event": "token", "content": "mock-answer"})
        return {"final_response": "mock-answer", "current_step": "respond"}

    collect_calls = {"n": 0}

    async def _mock_collect_node(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        collect_calls["n"] += 1
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] collect_node\n\n"})
        return {
            "context_dom": _long_dom_body(),
            "current_step": COLLECT_NODE,
            "executed_steps": [COLLECT_NODE],
        }

    async def _mock_eval_sufficient(state: dict[str, Any]) -> dict[str, Any]:
        from app.agents.archiver.models import Evaluation

        ev = Evaluation(
            is_sufficient=True,
            reason="scenario",
            recommended_action="none",
            dom_verdict="sufficient",
            rag_verdict="not_run",
            search_verdict="not_run",
        )
        writer = get_stream_writer()
        writer({"event": "status", "content": "[mock] evaluator ok\n\n"})
        return {"evaluation_result": ev.to_state_dict(), "current_step": "evaluator"}

    # scenario2 runtime: turn1 need_dom, turn2 collect → respond
    async def _mock_classify_collect(state: dict[str, Any]) -> dict[str, Any]:
        writer = get_stream_writer()
        writer(
            {
                "event": "status",
                "content": "[mock] parallel targets=collect_node\n\n",
            }
        )
        return {
            "is_general": False,
            "target_engines": [COLLECT_NODE],
            "current_step": "router",
        }

    async def _mock_classify_general(state: dict[str, Any]) -> dict[str, Any]:
        writer = get_stream_writer()
        writer({"event": "status", "content": MSG_ROUTER_GENERAL + "\n\n"})
        return {
            "is_general": True,
            "target_engines": [],
            "current_step": "router",
        }

    engine = ArchiverEngine()
    turn1 = ArchiverEngine.build_initial_state(
        messages=[HumanMessage(content="이거 뭐야?")],
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        session_id="scenario-dom-turn1",
        context_title="Example",
        context_url="https://example.com/page",
    )
    events_turn1: list[str] = []
    patches_turn1 = [
        patch("app.agents.archiver.workflow.classify", new=_mock_classify_collect),
        patch("app.agents.archiver.workflow.respond", new=_mock_respond),
    ]
    for p in patches_turn1:
        p.start()
    try:
        import app.agents.archiver.engine as engine_mod

        engine_mod._compiled_graph = build_archiver_engine()
        engine._graph = engine_mod._compiled_graph
        async for event in engine.stream(initial_state=turn1, store=None):
            events_turn1.append(event.event)
    finally:
        for p in patches_turn1:
            p.stop()

    _assert(
        "need_dom" in events_turn1 and "token" not in events_turn1,
        "scenario2-runtime: turn1 emits need_dom without respond token",
        errors,
    )

    turn2 = ArchiverEngine.build_initial_state(
        messages=[HumanMessage(content="이거 뭐야?")],
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        session_id="scenario-dom-turn2",
        context_title="Example",
        context_url="https://example.com/page",
        context_body=_long_dom_body(),
        dom_continuation=True,
    )
    tokens_turn2: list[str] = []
    patches_turn2 = [
        patch("app.agents.archiver.workflow.classify", new=_mock_classify_collect),
        patch("app.agents.archiver.workflow.collect_node", new=_mock_collect_node),
        patch("app.agents.archiver.workflow.evaluate", new=_mock_eval_sufficient),
        patch("app.agents.archiver.workflow.respond", new=_mock_respond),
    ]
    for p in patches_turn2:
        p.start()
    try:
        import app.agents.archiver.engine as engine_mod

        engine_mod._compiled_graph = build_archiver_engine()
        engine._graph = engine_mod._compiled_graph
        async for event in engine.stream(initial_state=turn2, store=None):
            if event.event == "token":
                tokens_turn2.append(event.content)
    finally:
        for p in patches_turn2:
            p.stop()

    _assert(collect_calls["n"] >= 1, "scenario2-runtime: turn2 runs collect_node", errors)
    _assert(tokens_turn2 == ["mock-answer"], "scenario2-runtime: turn2 reaches respond", errors)

    # scenario4 runtime: follow-up GENERAL → respond only
    followup_state = ArchiverEngine.build_initial_state(
        messages=[
            HumanMessage(content="GIL이 뭐야?"),
            AIMessage(content="GIL은 Global Interpreter Lock입니다."),
            HumanMessage(content="이거 더 쉽게"),
        ],
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        session_id="scenario-followup",
        context_title="Python docs",
        context_url="https://example.com/python",
        context_body=_long_dom_body(),
    )
    statuses: list[str] = []
    tokens: list[str] = []
    patches_followup = [
        patch("app.agents.archiver.workflow.classify", new=_mock_classify_general),
        patch("app.agents.archiver.workflow.collect_node", new=_mock_collect_node),
        patch("app.agents.archiver.workflow.search_node", new=AsyncMock()),
        patch("app.agents.archiver.workflow.respond", new=_mock_respond),
    ]
    for p in patches_followup:
        p.start()
    try:
        import app.agents.archiver.engine as engine_mod

        engine_mod._compiled_graph = build_archiver_engine()
        engine._graph = engine_mod._compiled_graph
        async for event in engine.stream(initial_state=followup_state, store=None):
            if event.event == "status":
                statuses.append(event.content)
            elif event.event == "token":
                tokens.append(event.content)
    finally:
        for p in patches_followup:
            p.stop()

    _assert(
        collect_calls["n"] == 1,
        "scenario4-runtime: follow-up does not invoke collect_node again",
        errors,
    )
    _assert(
        any(MSG_ROUTER_GENERAL in s for s in statuses),
        "scenario4-runtime: GENERAL status emitted",
        errors,
    )
    _assert(tokens == ["mock-answer"], "scenario4-runtime: respond token emitted", errors)

    # scenario4 classify path: dialogue follow-up can resolve to GENERAL without engines
    with patch(
        "app.agents.archiver.steps.classify._invoke_router_llm",
        new=AsyncMock(return_value=RouterTargets(targets=[], is_general=True)),
    ):
        targets, _, is_general = await _resolve_router_targets(
            "이거 더 쉽게",
            context_url="https://example.com/python",
            context_title="Python docs",
            recent_dialogue="어시스턴트: GIL은 Global Interpreter Lock입니다.",
        )
    _assert(
        targets == [] and is_general,
        "scenario4: dialogue follow-up LLM -> GENERAL without targets",
        errors,
    )


def main() -> int:
    errors = run_scenario_tests()
    asyncio.run(_run_engine_scenarios(errors))
    if errors:
        print("[FAIL] archiver_test_scenarios")
        for err in errors:
            print(f" - {err}")
        return 1
    print("[PASS] archiver_test_scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
