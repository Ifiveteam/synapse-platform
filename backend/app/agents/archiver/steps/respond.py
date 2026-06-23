"""respond 스텝 — 수집·평가 결과를 바탕으로 최종 LLM 응답을 스트리밍 생성한다."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from app.agents.archiver.core.constants import (
    RESPOND_DEFAULT_TEMPERATURE,
    RESPOND_TEMPERATURES,
    STREAM_ERROR_MESSAGE,
)
from app.agents.archiver.core.gemini import GEMINI_MODEL, get_client
from app.agents.archiver.protocols.stream_status import MSG_RESPOND_GENERATING, status_event
from app.agents.archiver.steps.respond_context import (
    build_gemini_contents,
    resolve_system_instruction,
)
from app.agents.archiver.trace import log_node_enter, log_respond_result
from app.agents.archiver.models import ArchiverState, resolve_route

logger = logging.getLogger(__name__)


async def respond(state: ArchiverState) -> dict[str, Any]:
    """최종 답변을 Gemini 스트리밍으로 생성하고 custom stream 이벤트를 방출한다."""
    log_node_enter("respond", state=state)
    route = resolve_route(state)
    route_value = route.value
    system_instruction, tools = resolve_system_instruction(state)
    temperature = RESPOND_TEMPERATURES.get(route.value, RESPOND_DEFAULT_TEMPERATURE)
    writer = get_stream_writer()
    gemini_contents = build_gemini_contents(state.get("messages", []))

    writer(status_event(MSG_RESPOND_GENERATING))

    chunks: list[str] = []

    try:
        stream = await get_client().aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=gemini_contents,
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
