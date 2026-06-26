"""Archiver respond — system_instruction·tool·Gemini contents 조립."""

from __future__ import annotations

from google.genai import types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.archiver.core.tools import GOOGLE_SEARCH_TOOL
from app.agents.archiver.prompts import (
    build_general_route_instruction,
    build_synthesis_route_instruction,
)
from app.agents.archiver.models import (
    SEARCH_NODE,
    ArchiverState,
    get_context_dom,
    get_context_rag,
    get_context_search,
    normalize_target_engines,
)


def _has_collected_evidence(*, context_dom: str, context_rag: str, context_search: str) -> bool:
    return any(value.strip() for value in (context_dom, context_rag, context_search))


def resolve_respond_tools(
    context_search: str,
    *,
    target_engines: list[str] | None = None,
) -> list[types.Tool] | None:
    """Google Search Tool — search_node 타겟인데 검색 미수집 시."""
    if context_search.strip():
        return None
    targets = set(normalize_target_engines(target_engines))
    if SEARCH_NODE in targets:
        return [GOOGLE_SEARCH_TOOL]
    return None


def resolve_system_instruction(
    state: ArchiverState,
) -> tuple[str, list[types.Tool] | None]:
    """채워진 context_* 기반 synthesis 또는 general 프롬프트를 조립한다."""
    context_dom = get_context_dom(state)
    context_rag = get_context_rag(state)
    context_search = get_context_search(state)
    target_engines = normalize_target_engines(state.get("target_engines"))
    has_evidence = _has_collected_evidence(
        context_dom=context_dom,
        context_rag=context_rag,
        context_search=context_search,
    )

    if state.get("is_general") and not has_evidence:
        return build_general_route_instruction(), None

    instruction = build_synthesis_route_instruction(
        context_title=state.get("context_title"),
        context_url=state.get("context_url"),
        context_dom=context_dom,
        context_rag=context_rag,
        context_search=context_search,
    )
    tools = resolve_respond_tools(context_search, target_engines=target_engines)
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
