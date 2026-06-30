"""Archiver respond — system_instruction·tool·Gemini contents 조립."""

from __future__ import annotations

from google.genai import types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.archiver.core.tools import (
    GOOGLE_SEARCH_TOOL,
    SCRAP_CURRENT_PAGE_TOOL,
)
from app.agents.archiver.models import (
    SEARCH_NODE,
    ArchiverState,
    get_context_dom,
    get_context_rag,
    get_context_search,
    get_scrapped_content,
    get_scrapped_summary,
    is_page_scrap_completed,
    is_scrap_followup_pass,
    normalize_target_engines,
    scrap_tool_already_executed,
)
from app.agents.archiver.prompts import (
    build_general_route_instruction,
    build_scrap_followup_summary_instruction,
    build_synthesis_route_instruction,
)


def _has_collected_evidence(
    *, context_dom: str, context_rag: str, context_search: str
) -> bool:
    return any(value.strip() for value in (context_dom, context_rag, context_search))


def resolve_respond_tools(
    context_search: str,
    *,
    target_engines: list[str] | None = None,
    include_scrap_tool: bool = True,
) -> list[types.Tool]:
    """respond 단계 Gemini Tool 목록 — 스크랩 도구는 조건부, 검색은 조건부."""
    tools: list[types.Tool] = []
    if include_scrap_tool:
        tools.append(SCRAP_CURRENT_PAGE_TOOL)
    if not context_search.strip():
        targets = set(normalize_target_engines(target_engines))
        if SEARCH_NODE in targets:
            tools.append(GOOGLE_SEARCH_TOOL)
    return tools


def resolve_system_instruction(
    state: ArchiverState,
) -> tuple[str, list[types.Tool]]:
    """채워진 context_*·scrapped_*·respond 루프 패스 기반 프롬프트를 조립한다."""
    if is_scrap_followup_pass(state):
        return (
            build_scrap_followup_summary_instruction(
                context_title=state.get("context_title"),
                context_url=state.get("context_url"),
                context_dom=get_context_dom(state) or get_scrapped_content(state),
                scrap_confirmation_text=state.get("scrap_confirmation_text"),
            ),
            [],
        )

    context_dom = get_context_dom(state)
    context_rag = get_context_rag(state)
    context_search = get_context_search(state)
    scrapped_content = get_scrapped_content(state)
    scrapped_summary = get_scrapped_summary(state)
    page_scrap_completed = is_page_scrap_completed(state)
    target_engines = normalize_target_engines(state.get("target_engines"))
    has_evidence = _has_collected_evidence(
        context_dom=context_dom,
        context_rag=context_rag,
        context_search=context_search,
    ) or bool(scrapped_content)
    include_scrap_tool = not page_scrap_completed and not scrap_tool_already_executed(
        state
    )

    if state.get("is_general") and not has_evidence:
        general_tools = [SCRAP_CURRENT_PAGE_TOOL] if include_scrap_tool else []
        return (
            build_general_route_instruction(
                scrapped_content=scrapped_content,
                scrapped_summary=scrapped_summary,
                page_scrap_completed=page_scrap_completed,
            ),
            general_tools,
        )

    instruction = build_synthesis_route_instruction(
        context_title=state.get("context_title"),
        context_url=state.get("context_url"),
        context_dom=context_dom,
        context_rag=context_rag,
        context_search=context_search,
        scrapped_content=scrapped_content,
        scrapped_summary=scrapped_summary,
        page_scrap_completed=page_scrap_completed,
    )
    tools = resolve_respond_tools(
        context_search,
        target_engines=target_engines,
        include_scrap_tool=include_scrap_tool,
    )
    return instruction, tools


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return str(content)


def build_gemini_contents(messages: list[BaseMessage]) -> str | list[types.Content]:
    """LangGraph messages를 Gemini multi-turn contents로 변환한다."""
    if not messages:
        return ""

    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
        return _message_text(messages[0])

    gemini_contents: list[types.Content] = []
    for message in messages:
        text = _message_text(message)
        if not text.strip():
            continue
        if isinstance(message, HumanMessage):
            gemini_contents.append(
                types.Content(role="user", parts=[types.Part(text=text)])
            )
        elif isinstance(message, AIMessage):
            gemini_contents.append(
                types.Content(role="model", parts=[types.Part(text=text)])
            )

    if not gemini_contents:
        return ""
    if len(gemini_contents) == 1 and gemini_contents[0].role == "user":
        return gemini_contents[0].parts[0].text or ""
    return gemini_contents
