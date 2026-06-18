"""respond 스텝 — 수집·평가 결과를 바탕으로 최종 LLM 응답을 스트리밍 생성한다."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from app.agents.archiver.constants import (
    RESPOND_DEFAULT_TEMPERATURE,
    RESPOND_TEMPERATURES,
    STREAM_ERROR_MESSAGE,
)
from app.agents.archiver.gemini import GEMINI_MODEL, get_client
from app.agents.archiver.prompts import (
    build_basic_route_instruction,
    build_general_route_instruction,
    build_rag_route_instruction,
    build_search_route_instruction,
)
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.trace import log_node_enter, log_respond_result
from app.agents.archiver.types import (
    ArchiverRoute,
    ArchiverState,
    Evaluation,
    resolve_route,
)

logger = logging.getLogger(__name__)
_GOOGLE_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


def resolve_system_instruction(state: ArchiverState) -> tuple[str, list[types.Tool] | None]:
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
            instruction += f"\n\n[검색 수집 결과]\n{search_data}"
        tools = [_GOOGLE_SEARCH_TOOL] if route == ArchiverRoute.SEARCH else None
        return instruction, tools

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


async def respond(state: ArchiverState) -> dict[str, Any]:
    """최종 답변을 Gemini 스트리밍으로 생성하고 custom stream 이벤트를 방출한다."""
    log_node_enter("respond", state=state)
    user_message = latest_user_message(state)
    route = resolve_route(state)
    route_value = route.value
    system_instruction, tools = resolve_system_instruction(state)
    temperature = RESPOND_TEMPERATURES.get(route.value, RESPOND_DEFAULT_TEMPERATURE)
    writer = get_stream_writer()

    writer(
        {
            "event": "status",
            "content": "✨ [Respond] 최종 답변을 생성합니다...\n\n",
        }
    )

    chunks: list[str] = []

    try:
        stream = await get_client().aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools,
                temperature=temperature,
            ),
        )
        async for chunk in stream:
            if chunk.text:
                chunks.append(chunk.text)
                writer({"event": "token", "content": chunk.text})
    except Exception:
        logger.exception("Archiver respond stream failed route=%s", route)
        writer({"event": "token", "content": STREAM_ERROR_MESSAGE})
        log_respond_result(
            route=route_value,
            response_chars=len(STREAM_ERROR_MESSAGE),
            temperature=temperature,
            has_error=True,
        )
        return {
            "final_response": STREAM_ERROR_MESSAGE,
            "system_instruction": system_instruction,
            "current_step": "respond",
            "error": STREAM_ERROR_MESSAGE,
        }

    final_response = "".join(chunks)
    log_respond_result(
        route=route_value,
        response_chars=len(final_response),
        temperature=temperature,
        has_error=False,
    )
    return {
        "final_response": final_response,
        "system_instruction": system_instruction,
        "messages": [AIMessage(content=final_response)],
        "current_step": "respond",
    }
