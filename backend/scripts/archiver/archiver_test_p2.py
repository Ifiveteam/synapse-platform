"""Archiver P2 테스트 — SSE·multi-turn·respond tool binding."""

from __future__ import annotations

import sys

from langchain_core.messages import HumanMessage

from app.agents.archiver.core.constants import (
    RESPOND_CHITCHAT_TEMPERATURE,
    RESPOND_FACTUAL_TEMPERATURE,
)
from app.agents.archiver.core.history import append_user_turn, history_to_messages
from app.agents.archiver.core.tools import GOOGLE_SEARCH_TOOL, SCRAP_CURRENT_PAGE_TOOL
from app.agents.archiver.models import SEARCH_NODE, ArchiverStreamEvent
from app.agents.archiver.protocols.stream_status import (
    status_event,
    trigger_web_scrap_event,
)
from app.agents.archiver.protocols.streaming import (
    format_sse_event,
    format_stream_event,
)
from app.agents.archiver.steps.respond_context import (
    build_gemini_contents,
    resolve_respond_tools,
    resolve_system_instruction,
)
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

    structured = status_event(
        "병렬 수집 중",
        phase="router_parallel",
        engines=[SEARCH_NODE, "collect_node"],
    )
    sse_structured = format_stream_event(
        ArchiverStreamEvent(
            event="status",
            content=structured["content"],
            phase="router_parallel",
            engines=(SEARCH_NODE, "collect_node"),
            message=structured["message"],
        )
    )
    _assert(
        '"phase": "router_parallel"' in sse_structured, "SSE: structured phase", errors
    )
    _assert('"engines"' in sse_structured, "SSE: structured engines", errors)
    _assert('"message"' in sse_structured, "SSE: structured message", errors)
    _assert('"content"' in sse_structured, "SSE: legacy content field", errors)

    legacy = format_sse_event(event="status", content="안내\n\n")
    _assert(
        '"content"' in legacy and '"phase"' not in legacy,
        "SSE: legacy without phase",
        errors,
    )

    action_frame = format_sse_event(
        event="action",
        content="스크랩 준비",
        action="TRIGGER_WEB_SCRAP",
    )
    _assert(
        '"action": "TRIGGER_WEB_SCRAP"' in action_frame, "SSE: action payload", errors
    )

    scrap_signal = trigger_web_scrap_event(custom_category="레시피")
    _assert(scrap_signal["event"] == "action", "scrap signal: action event", errors)
    _assert(
        scrap_signal["action"] == "TRIGGER_WEB_SCRAP",
        "scrap signal: TRIGGER_WEB_SCRAP",
        errors,
    )
    _assert(
        scrap_signal.get("custom_category") == "레시피",
        "scrap signal: custom_category",
        errors,
    )

    # multi-turn history
    history = [
        ArchiverChatMessage(
            id=1, role="user", content="이전 질문", created_at="2026-06-18T00:00:00Z"
        ),  # type: ignore[arg-type]
        ArchiverChatMessage(
            id=2, role="assistant", content="이전 답", created_at="2026-06-18T00:00:01Z"
        ),  # type: ignore[arg-type]
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
    search_tools = resolve_respond_tools("", target_engines=[SEARCH_NODE])
    _assert(
        SCRAP_CURRENT_PAGE_TOOL in search_tools,
        "tools: scrap always bound",
        errors,
    )
    _assert(
        GOOGLE_SEARCH_TOOL in search_tools,
        "tools: search_node without context_search binds search",
        errors,
    )
    no_search_tools = resolve_respond_tools("이미 수집됨", target_engines=[SEARCH_NODE])
    _assert(
        SCRAP_CURRENT_PAGE_TOOL in no_search_tools,
        "tools: scrap bound when search already collected",
        errors,
    )
    _assert(
        GOOGLE_SEARCH_TOOL not in no_search_tools,
        "tools: search_node with context_search skips search tool",
        errors,
    )
    collect_only_tools = resolve_respond_tools(
        "보완 검색", target_engines=["collect_node"]
    )
    _assert(
        collect_only_tools == [SCRAP_CURRENT_PAGE_TOOL],
        "tools: collect_node only binds scrap tool",
        errors,
    )

    instruction, tools = resolve_system_instruction(
        {
            "is_general": False,
            "target_engines": ["collect_node", "search_node"],
            "context_title": "t",
            "context_url": "http://x",
            "context_dom": "page body",
            "context_search": "web hits",
        }
    )
    _assert(len(tools) == 1, "resolve: dom+search parallel scrap tool only", errors)
    _assert("page body" in instruction, "resolve: dom+search includes dom", errors)
    _assert("web hits" in instruction, "resolve: dom+search includes search", errors)
    _assert(
        "[현재 페이지 본문]" in instruction and "[웹 검색 결과]" in instruction,
        "resolve: dom+search has both section headers",
        errors,
    )

    instruction, tools = resolve_system_instruction(
        {
            "is_general": False,
            "target_engines": ["collect_node"],
            "context_title": "t",
            "context_url": "http://x",
            "context_dom": "body",
            "context_search": "cached search",
        }
    )
    _assert(len(tools) == 1, "resolve: BASIC+context_search scrap tool only", errors)
    _assert("body" in instruction, "resolve: BASIC+context_search includes dom", errors)
    _assert(
        "cached search" in instruction,
        "resolve: BASIC+context_search includes search",
        errors,
    )

    general_instruction, general_tools = resolve_system_instruction(
        {"is_general": True}
    )
    _assert(len(general_tools) == 1, "resolve: is_general has scrap tool", errors)
    _assert("일상 대화" in general_instruction, "resolve: is_general template", errors)

    synthesis_instruction, _ = resolve_system_instruction(
        {
            "is_general": True,
            "target_engines": [],
            "context_dom": "leftover dom",
        }
    )
    _assert(
        "leftover dom" in synthesis_instruction,
        "resolve: is_general with evidence uses synthesis",
        errors,
    )
    _assert(
        "일상 대화" not in synthesis_instruction,
        "resolve: is_general with evidence skips general template",
        errors,
    )

    _assert(
        RESPOND_CHITCHAT_TEMPERATURE > RESPOND_FACTUAL_TEMPERATURE,
        "temperature: chitchat warmer than factual",
        errors,
    )

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
