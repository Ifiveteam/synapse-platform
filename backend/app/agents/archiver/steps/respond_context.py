"""Archiver respond — system_instruction·tool·Gemini contents 조립."""

from __future__ import annotations

from google.genai import types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.archiver.tools import GOOGLE_SEARCH_TOOL
from app.agents.archiver.prompts import (
    build_basic_route_instruction,
    build_general_route_instruction,
    build_rag_route_instruction,
    build_search_route_instruction,
)
from app.agents.archiver.types import (
    ArchiverRoute,
    ArchiverState,
    Evaluation,
    resolve_route,
)


def resolve_respond_tools(
    route: ArchiverRoute,
    search_data: str,
) -> list[types.Tool] | None:
    """Google Search Tool은 SEARCH 경로이면서 수집된 search_data가 없을 때만 바인딩."""
    if route == ArchiverRoute.SEARCH and not search_data:
        return [GOOGLE_SEARCH_TOOL]
    return None


def resolve_system_instruction(
    state: ArchiverState,
) -> tuple[str, list[types.Tool] | None]:
    """수집된 근거와 route에 따라 respond용 system_instruction을 조립한다."""
    route = resolve_route(state)
    rag_data = (state.get("rag_data") or "").strip()
    search_data = (state.get("search_data") or "").strip()
    evaluation = Evaluation.from_state(state)

    if route == ArchiverRoute.RAG and rag_data:
        return build_rag_route_instruction(past_rag_knowledge=rag_data), None

    if route == ArchiverRoute.BASIC:
        instruction = build_basic_route_instruction(
            context_title=state.get("context_title"),
            context_url=state.get("context_url"),
            context_body=state.get("context_body"),
        )
        if search_data:
            instruction += f"\n\n[웹 검색 보완 결과]\n{search_data}"
        return instruction, None

    if route == ArchiverRoute.SEARCH or search_data:
        instruction = build_search_route_instruction(
            context_title=state.get("context_title"),
            context_url=state.get("context_url"),
        )
        if search_data:
            instruction += (
                f"\n\n[검색 수집 결과]\n{search_data}\n\n"
                "위 결과만 근거로 답하세요. 도구·검색 과정을 언급하지 마세요."
            )
        return instruction, resolve_respond_tools(route, search_data)

    if route == ArchiverRoute.RAG and not rag_data:
        if search_data:
            instruction = build_search_route_instruction(
                context_title=state.get("context_title"),
                context_url=state.get("context_url"),
            )
            instruction += f"\n\n[RAG 미매칭 — 검색 대체 결과]\n{search_data}"
            return instruction, None
        if evaluation is not None and not evaluation.is_sufficient:
            return build_general_route_instruction(), None

    return build_general_route_instruction(), None


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
