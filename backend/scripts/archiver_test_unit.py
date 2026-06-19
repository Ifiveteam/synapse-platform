"""Archiver 단위 테스트 — branches, route 파싱, Evaluation fallback."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch

from app.agents.archiver.branches import (
    route_after_collect,
    route_after_evaluator,
    route_after_router,
)
from app.agents.archiver.constants import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
    STREAM_ERROR_MESSAGE,
    STREAM_ERROR_PREFIX,
)
from app.agents.archiver.router_heuristics import detect_route_heuristic
from app.agents.archiver.types import (
    ArchiverRoute,
    Evaluation,
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
) -> dict[str, Any]:
    evaluation = Evaluation(
        is_sufficient=sufficient,
        score=90 if sufficient else 30,
        reason="test",
        recommended_action=action,  # type: ignore[arg-type]
    )
    return {
        "evaluation_result": evaluation.to_state_dict(),
        "search_attempts": search_attempts,
        "retrieval_attempts": retrieval_attempts,
    }


def run_unit_tests() -> list[str]:
    errors: list[str] = []

    # parse_archiver_route
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

    # router heuristics
    _assert(
        detect_route_heuristic("search를 사용해서 답해줘") == ArchiverRoute.SEARCH,
        "heuristic: explicit search request",
        errors,
    )
    _assert(
        detect_route_heuristic("오늘 서울 날씨 알려줘") == ArchiverRoute.SEARCH,
        "heuristic: weather question",
        errors,
    )
    _assert(
        detect_route_heuristic("안녕") == ArchiverRoute.GENERAL,
        "heuristic: greeting",
        errors,
    )
    _assert(
        detect_route_heuristic("예전에 저장한 맛집 기록 보여줘") == ArchiverRoute.RAG,
        "heuristic: rag hint",
        errors,
    )

    # resolve_route
    _assert(
        resolve_route({"route": ArchiverRoute.BASIC}) == ArchiverRoute.BASIC,
        "resolve_route: enum",
        errors,
    )
    _assert(
        resolve_route({"route": "SEARCH"}) == ArchiverRoute.SEARCH,
        "resolve_route: str",
        errors,
    )
    _assert(
        resolve_route({}) == ArchiverRoute.GENERAL,
        "resolve_route: missing -> GENERAL",
        errors,
    )

    # Evaluation.fallback
    fb_search = Evaluation.fallback(
        state={"route": ArchiverRoute.RAG, "search_attempts": 0},
    )
    _assert(
        fb_search.recommended_action == "search",
        "fallback: RAG with attempts -> search",
        errors,
    )

    fb_respond = Evaluation.fallback(
        state={"route": ArchiverRoute.RAG, "search_attempts": MAX_SEARCH_ATTEMPTS},
    )
    _assert(
        fb_respond.recommended_action == "respond",
        "fallback: attempts exhausted -> respond",
        errors,
    )

    # constants SSOT
    _assert(
        STREAM_ERROR_MESSAGE.startswith(STREAM_ERROR_PREFIX),
        "STREAM_ERROR_MESSAGE uses STREAM_ERROR_PREFIX",
        errors,
    )

    with (
        patch("app.agents.archiver.branches.log_router_branch"),
        patch("app.agents.archiver.branches.log_evaluator_branch"),
    ):
        # route_after_router
        _assert(
            route_after_router({"route": ArchiverRoute.GENERAL}) == "respond",
            "router: GENERAL -> respond",
            errors,
        )
        _assert(
            route_after_router({"route": ArchiverRoute.SEARCH}) == "search",
            "router: SEARCH -> search",
            errors,
        )
        _assert(
            route_after_router({"route": ArchiverRoute.RAG}) == "collect",
            "router: RAG -> collect",
            errors,
        )
        _assert(
            route_after_router({"route": ArchiverRoute.BASIC}) == "collect",
            "router: BASIC -> collect",
            errors,
        )

        _assert(route_after_collect({}) == "evaluator", "collect -> evaluator", errors)

        # route_after_evaluator
        _assert(
            route_after_evaluator({}) == "respond",
            "evaluator: missing evaluation -> respond",
            errors,
        )
        _assert(
            route_after_evaluator(_eval_state(sufficient=True, action="respond"))
            == "respond",
            "evaluator: sufficient -> respond",
            errors,
        )
        _assert(
            route_after_evaluator(
                _eval_state(sufficient=False, action="search", search_attempts=0),
            )
            == "search",
            "evaluator: search recommended with budget -> search",
            errors,
        )
        _assert(
            route_after_evaluator(
                _eval_state(
                    sufficient=False,
                    action="search",
                    search_attempts=MAX_SEARCH_ATTEMPTS,
                ),
            )
            == "respond",
            "evaluator: search budget exhausted -> respond",
            errors,
        )
        _assert(
            route_after_evaluator(
                _eval_state(
                    sufficient=False,
                    action="collect",
                    retrieval_attempts=0,
                ),
            )
            == "collect",
            "evaluator: collect recommended with budget -> collect",
            errors,
        )
        _assert(
            route_after_evaluator(
                _eval_state(
                    sufficient=False,
                    action="collect",
                    retrieval_attempts=MAX_RETRIEVAL_ATTEMPTS,
                ),
            )
            == "respond",
            "evaluator: collect budget exhausted -> respond",
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
