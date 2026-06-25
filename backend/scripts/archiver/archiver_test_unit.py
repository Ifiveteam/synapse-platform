"""Archiver 단위 테스트 — branches, trace 라벨, Evaluation fallback."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Send

from app.agents.archiver.branches import route_after_evaluator, route_after_router
from app.agents.archiver.steps.classify import normalize_router_decision
from app.agents.archiver.prompts.router_prompt import build_router_prompt
from app.agents.archiver.utils.router_heuristics import (
    is_greeting_preflight,
    needs_dialogue_context,
    resolve_router_dialogue_context,
)
from app.agents.archiver.models import (
    COLLECT_NODE,
    RAG_NODE,
    SEARCH_NODE,
    normalize_target_engines,
)
from app.agents.archiver.core.constants import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
    STREAM_ERROR_MESSAGE,
    STREAM_ERROR_PREFIX,
)
from app.agents.archiver.models import (
    Evaluation,
    RouterTargets,
    format_router_trace_label,
    get_context_dom,
    get_context_rag,
    get_context_search,
)


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _eval_state(
    *,
    sufficient: bool,
    action: str,
    search_attempts: int = 0,
    retrieval_attempts: int = 0,
    executed_steps: list[str] | None = None,
) -> dict[str, Any]:
    evaluation = Evaluation(
        is_sufficient=sufficient,
        reason="test",
        recommended_action=action,  # type: ignore[arg-type]
        dom_verdict="sufficient" if sufficient else "insufficient",
        rag_verdict="not_run",
        search_verdict="not_run",
    )
    return {
        "evaluation_result": evaluation.to_state_dict(),
        "search_attempts": search_attempts,
        "retrieval_attempts": retrieval_attempts,
        "executed_steps": executed_steps or [],
        "target_engines": [COLLECT_NODE, RAG_NODE, SEARCH_NODE],
    }


def run_unit_tests() -> list[str]:
    errors: list[str] = []

    _assert(
        format_router_trace_label(is_general=True) == "general",
        "trace_label: is_general",
        errors,
    )
    _assert(
        format_router_trace_label(target_engines=[SEARCH_NODE]) == "search_node",
        "trace_label: single engine",
        errors,
    )
    _assert(
        format_router_trace_label(target_engines=[COLLECT_NODE, SEARCH_NODE])
        == "collect_node+search_node",
        "trace_label: multi-engine join",
        errors,
    )
    _assert(
        format_router_trace_label(
            {"is_general": False, "target_engines": [RAG_NODE, SEARCH_NODE]}
        )
        == "rag_node+search_node",
        "trace_label: from state",
        errors,
    )

    _assert(
        get_context_dom({"context_dom": "canonical"}) == "canonical",
        "get_context_dom: canonical field",
        errors,
    )
    _assert(
        get_context_dom({"context_body": "legacy"}) == "legacy",
        "get_context_dom: legacy context_body fallback",
        errors,
    )
    _assert(
        get_context_rag({"rag_data": "legacy rag"}) == "legacy rag",
        "get_context_rag: legacy rag_data fallback",
        errors,
    )
    _assert(
        get_context_search({"search_data": "legacy search"}) == "legacy search",
        "get_context_search: legacy search_data fallback",
        errors,
    )

    ev = Evaluation(
        is_sufficient=False,
        reason="test",
        recommended_action="search",
        dom_verdict="insufficient",
        rag_verdict="not_run",
        search_verdict="not_run",
    )
    roundtrip = Evaluation.from_state({"evaluation_result": ev.to_state_dict()})
    _assert(roundtrip is not None and roundtrip.recommended_action == "search", "from_state: roundtrip", errors)

    from app.agents.archiver.nodes.utils.scraper import (
        is_usable_context_body,
        normalize_client_context_body,
    )

    _assert(
        is_usable_context_body("x" * 100),
        "context_body: usable when long enough",
        errors,
    )
    _assert(
        not is_usable_context_body("짧음"),
        "context_body: too short rejected",
        errors,
    )
    _assert(
        normalize_client_context_body("  " + "a" * 100 + "  ") == "a" * 100,
        "context_body: normalize trims",
        errors,
    )

    from app.agents.archiver.utils.context_refine import (
        clean_context_title,
        clean_context_url,
        extract_url_search_hint,
        is_thin_context_body,
    )
    from app.agents.archiver.utils.search_query import build_search_user_content

    _assert(
        clean_context_title("네이버 지도 - 네이버") == "네이버 지도",
        "search_query: strip title suffix",
        errors,
    )
    _assert(
        "utm_source" not in clean_context_url("https://example.com?utm_source=x"),
        "search_query: strip tracking params",
        errors,
    )

    fb = Evaluation.fallback(state={"executed_steps": [], "search_attempts": 0})
    _assert(fb.recommended_action == "search", "fallback: default search retry", errors)

    _assert(
        STREAM_ERROR_MESSAGE.startswith(STREAM_ERROR_PREFIX),
        "STREAM_ERROR_MESSAGE uses STREAM_ERROR_PREFIX",
        errors,
    )

    with (
        patch("app.agents.archiver.branches.log_router_branch"),
        patch("app.agents.archiver.branches.log_evaluator_branch"),
    ):
        _assert(
            route_after_router({"is_general": True}) == "respond",
            "router: GENERAL fast-path -> respond",
            errors,
        )

        need_dom = route_after_router(
            {
                "target_engines": [COLLECT_NODE],
                "context_dom": "",
            }
        )
        _assert(need_dom == "need_dom", "router: missing DOM -> need_dom", errors)

        fan_out = route_after_router(
            {
                "target_engines": [SEARCH_NODE, RAG_NODE],
            }
        )
        _assert(
            isinstance(fan_out, list)
            and all(isinstance(item, Send) for item in fan_out),
            "router: multi-target -> Send fan-out",
            errors,
        )

        _assert(
            route_after_evaluator({}) == "respond",
            "evaluator: missing evaluation -> respond",
            errors,
        )
        _assert(
            route_after_evaluator(_eval_state(sufficient=True, action="none")) == "respond",
            "evaluator: sufficient -> respond",
            errors,
        )

        search_retry = route_after_evaluator(
            _eval_state(
                sufficient=False,
                action="search",
                search_attempts=0,
                executed_steps=[RAG_NODE],
            )
        )
        _assert(
            isinstance(search_retry, list)
            and any(s.node == SEARCH_NODE for s in search_retry),
            "evaluator: search retry fan-out",
            errors,
        )

    _assert(is_greeting_preflight("ㅎㅇ"), "router_heuristics: greeting ㅎㅇ", errors)
    _assert(is_greeting_preflight("고마워!"), "router_heuristics: greeting thanks", errors)
    _assert(
        not is_greeting_preflight(""),
        "router_heuristics: empty is not greeting pattern",
        errors,
    )
    _assert(
        not is_greeting_preflight("이거 뭐야?"),
        "router_heuristics: deictic is not greeting",
        errors,
    )
    _assert(
        needs_dialogue_context("이거 더 쉽게 설명해줘"),
        "router_heuristics: follow-up needs dialogue",
        errors,
    )
    _assert(
        not needs_dialogue_context("오늘 서울 날씨 알려줘"),
        "router_heuristics: weather skips dialogue",
        errors,
    )

    dialogue_state = {
        "messages": [
            HumanMessage(content="GIL이 뭐야?"),
            AIMessage(content="GIL은 Global Interpreter Lock입니다."),
            HumanMessage(content="이거 더 쉽게"),
        ],
        "user_id": "00000000-0000-0000-0000-000000000001",
        "context_title": "t",
        "context_url": "https://example.com",
    }
    _assert(
        resolve_router_dialogue_context(dialogue_state, "이거 더 쉽게") is not None,
        "router_heuristics: resolve dialogue for follow-up",
        errors,
    )
    _assert(
        resolve_router_dialogue_context(dialogue_state, "오늘 서울 날씨") is None,
        "router_heuristics: resolve skips explicit query",
        errors,
    )

    prompt_without = build_router_prompt(context_url="https://x.com", context_title="t")
    _assert(
        "[직전 대화]" not in prompt_without,
        "router_prompt: omit dialogue block when None",
        errors,
    )
    _assert(
        "수집 계획기" in prompt_without,
        "router_prompt: collection planner framing",
        errors,
    )
    _assert(
        "[사용자 질문]" not in prompt_without,
        "router_prompt: user message only via user_content",
        errors,
    )

    prompt_with = build_router_prompt(
        context_url="https://x.com",
        context_title="t",
        recent_dialogue="어시스턴트: GIL은 ...",
    )
    _assert(
        "[직전 대화]" in prompt_with and "GIL은" in prompt_with,
        "router_prompt: include dialogue block when set",
        errors,
    )

    normalized_general = normalize_router_decision(
        RouterTargets(targets=[SEARCH_NODE], is_general=True)
    )
    _assert(
        normalized_general.is_general and not normalized_general.targets,
        "normalize: is_general clears targets",
        errors,
    )
    normalized_collect = normalize_router_decision(
        RouterTargets(targets=["collect_node", "search_node"], is_general=False)
    )
    _assert(
        normalized_collect.targets == [COLLECT_NODE, SEARCH_NODE],
        "normalize: multi-engine order",
        errors,
    )
    normalized_empty = normalize_router_decision(
        RouterTargets(targets=[], is_general=False)
    )
    _assert(
        normalized_empty.is_general and not normalized_empty.targets,
        "normalize: empty targets -> general",
        errors,
    )

    return errors


def main() -> int:
    errors = run_unit_tests()
    if errors:
        print("[FAIL] archiver_test_unit")
        for err in errors:
            print(f" - {err}")
        return 1
    print("[PASS] archiver_test_unit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
