"""Archiver P2 테스트 — SSE·multi-turn·respond tool binding."""

from __future__ import annotations

import sys

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.archiver.core.history import append_user_turn, history_to_messages
from app.agents.archiver.steps.respond_context import (
    build_gemini_contents,
    resolve_respond_tools,
    resolve_system_instruction,
)
from app.agents.archiver.protocols.streaming import format_sse_event
from app.agents.archiver.models import ArchiverRoute
from app.schemas.archiver import ArchiverChatMessage


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_p2_tests() -> list[str]:
    errors: list[str] = []

    # SSE envelope
    frame = format_sse_event(event="token", content="안녕")
    _assert(frame.startswith("event: token\n"), "SSE: event line", errors)
    _assert('"content": "안녕"' in frame, "SSE: JSON payload", errors)
    _assert(frame.endswith("\n\n"), "SSE: frame terminator", errors)

    # multi-turn history
    history = [
        ArchiverChatMessage(id=1, role="user", content="이전 질문", created_at="2026-06-18T00:00:00Z"),  # type: ignore[arg-type]
        ArchiverChatMessage(id=2, role="assistant", content="이전 답", created_at="2026-06-18T00:00:01Z"),  # type: ignore[arg-type]
    ]
    prior = history_to_messages(history, limit=20)
    full = append_user_turn(prior, "새 질문")
    _assert(len(full) == 3, "history: 3 messages", errors)
    _assert(isinstance(full[-1], HumanMessage), "history: last is user", errors)

    gemini_multi = build_gemini_contents(full)
    _assert(isinstance(gemini_multi, list), "gemini: multi-turn list", errors)
    _assert(len(gemini_multi) == 3, "gemini: 3 contents", errors)

    gemini_single = build_gemini_contents([HumanMessage(content="단일")])
    _assert(gemini_single == "단일", "gemini: single string shortcut", errors)

    # respond tool binding
    _assert(
        resolve_respond_tools(ArchiverRoute.SEARCH, "") is not None,
        "tools: SEARCH without search_data binds tool",
        errors,
    )
    _assert(
        resolve_respond_tools(ArchiverRoute.SEARCH, "이미 수집됨") is None,
        "tools: SEARCH with search_data skips tool",
        errors,
    )
    _assert(
        resolve_respond_tools(ArchiverRoute.BASIC, "보완 검색") is None,
        "tools: BASIC never binds search tool",
        errors,
    )

    instruction, tools = resolve_system_instruction(
        {
            "route": ArchiverRoute.BASIC,
            "context_title": "t",
            "context_url": "http://x",
            "context_body": "body",
            "search_data": "cached search",
        }
    )
    _assert(tools is None, "resolve: BASIC+cached search_data no tools", errors)
    _assert("cached search" in instruction, "resolve: search_data injected", errors)

    return errors


def main() -> int:
    errors = run_p2_tests()
    if errors:
        print("[FAIL] archiver_test_p2")
        for err in errors:
            print(f" - {err}")
        return 1
    print("[PASS] archiver_test_p2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
