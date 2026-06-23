"""Archiver 단위 테스트 — branches, route 파싱, Evaluation fallback."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch

from langgraph.types import Send

from app.agents.archiver.branches import route_after_evaluator, route_after_router
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
    ArchiverRoute,
    Evaluation,
    RouterTargets,
    derive_route_from_targets,
    parse_archiver_route,
    resolve_route,
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
        parse_archiver_route("GENERAL") == ArchiverRoute.GENERAL,
        "parse: exact GENERAL",
        errors,
    )
    _assert(
        parse_archiver_route("  search  ") == ArchiverRoute.SEARCH,
        "parse: trimmed SEARCH",
        errors,
    )
    _assert(
        parse_archiver_route("답: RAG 경로") == ArchiverRoute.RAG,
        "parse: substring RAG",
        errors,
    )
    _assert(
        parse_archiver_route("알 수 없음") == ArchiverRoute.GENERAL,
        "parse: unknown -> GENERAL fallback",
        errors,
    )
    _assert(
        parse_archiver_route("NOT GENERAL — SEARCH needed") == ArchiverRoute.SEARCH,
        "parse: SEARCH before GENERAL substring",
        errors,
    )

    from app.agents.archiver.steps.scraper import (
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

    _assert(
        derive_route_from_targets([SEARCH_NODE], is_general=False) == ArchiverRoute.SEARCH,
        "derive_route: single search_node",
        errors,
    )
    _assert(
        derive_route_from_targets([], is_general=True) == ArchiverRoute.GENERAL,
        "derive_route: general empty",
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
            route_after_router({"is_general": True, "route": ArchiverRoute.GENERAL})
            == "respond",
            "router: GENERAL fast-path -> respond",
            errors,
        )

        need_dom = route_after_router(
            {
                "route": ArchiverRoute.BASIC,
                "target_engines": [COLLECT_NODE],
                "context_body": "",
                "context_dom": "",
            }
        )
        _assert(need_dom == "need_dom", "router: missing DOM -> need_dom", errors)

        fan_out = route_after_router(
            {
                "route": ArchiverRoute.SEARCH,
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
