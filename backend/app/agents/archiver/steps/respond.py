"""respond 스텝 — 수집·평가 결과를 바탕으로 최종 LLM 응답을 스트리밍 생성한다."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from app.agents.archiver.core.constants import (
    RESPOND_CHITCHAT_TEMPERATURE,
    RESPOND_FACTUAL_TEMPERATURE,
    STREAM_ERROR_MESSAGE,
)
from app.agents.archiver.core.tools import SCRAP_CURRENT_PAGE_TOOL_NAME
from app.agents.archiver.models import (
    ArchiverState,
    format_router_trace_label,
    is_scrap_followup_pass,
    should_schedule_scrap_followup_summary,
)
from app.agents.archiver.protocols.stream_status import (
    MSG_RESPOND_GENERATING,
    status_event,
    trigger_web_scrap_event,
)
from app.agents.archiver.scrap.classifier import normalize_custom_category
from app.agents.archiver.steps.respond_context import (
    build_gemini_contents,
    resolve_system_instruction,
)
from app.agents.archiver.trace import log_node_enter, log_respond_result
from app.agents.shared.gemini import GEMINI_MODEL, get_client

logger = logging.getLogger(__name__)

SCRAP_CONFIRMATION_MESSAGE = (
    "📌 현재 페이지를 스크랩 보관함에 저장할게요. 잠시만 기다려 주세요!"
)
SCRAP_FOLLOWUP_BRIDGE = "\n\n이어서 페이지 내용을 요약해 드리겠습니다.\n\n"


def _function_call_from_part(part: Any) -> Any | None:
    return getattr(part, "function_call", None)


def _extract_scrap_tool_call(chunk: Any) -> dict[str, Any] | None:
    """Gemini 스트림 청크에서 scrap_current_page function call args를 추출한다."""
    function_calls = getattr(chunk, "function_calls", None)
    if function_calls:
        for function_call in function_calls:
            name = getattr(function_call, "name", None)
            if name != SCRAP_CURRENT_PAGE_TOOL_NAME:
                continue
            args = getattr(function_call, "args", None)
            return dict(args) if isinstance(args, dict) else {}

    candidates = getattr(chunk, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        for part in parts:
            function_call = _function_call_from_part(part)
            if not function_call:
                continue
            name = getattr(function_call, "name", None)
            if name != SCRAP_CURRENT_PAGE_TOOL_NAME:
                continue
            args = getattr(function_call, "args", None)
            return dict(args) if isinstance(args, dict) else {}

    return None


def _user_specified_category_from_tool_args(args: dict[str, Any]) -> str | None:
    raw = args.get("user_specified_category")
    if raw is None:
        return None
    return normalize_custom_category(str(raw))


def _respond_temperature(state: ArchiverState) -> float:
    return (
        RESPOND_CHITCHAT_TEMPERATURE
        if state.get("is_general")
        else RESPOND_FACTUAL_TEMPERATURE
    )


def _error_return(
    *,
    trace_label: str,
    system_instruction: str,
    temperature: float,
) -> dict[str, Any]:
    return {
        "final_response": STREAM_ERROR_MESSAGE,
        "system_instruction": system_instruction,
        "current_step": "respond",
        "error": STREAM_ERROR_MESSAGE,
    }


async def _stream_gemini_text(
    *,
    system_instruction: str,
    gemini_contents: str | list[types.Content],
    tools: list[types.Tool],
    temperature: float,
    writer: Any,
    allow_scrap_tool: bool,
) -> tuple[str, dict[str, Any] | None]:
    """Gemini 스트림에서 텍스트 또는 scrap 도구 호출을 수집한다."""
    chunks: list[str] = []
    scrap_tool_args: dict[str, Any] | None = None

    stream = await get_client().aio.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=gemini_contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools or None,
            temperature=temperature,
        ),
    )
    async for chunk in stream:
        if allow_scrap_tool:
            tool_args = _extract_scrap_tool_call(chunk)
            if tool_args is not None:
                scrap_tool_args = tool_args
                break
        if chunk.text:
            chunks.append(chunk.text)
            writer({"event": "token", "content": chunk.text})

    return "".join(chunks), scrap_tool_args


async def _respond_scrap_followup_summary(state: ArchiverState) -> dict[str, Any]:
    """2차 respond — 스크랩 확인 직후 동일 턴 페이지 요약을 스트리밍한다."""
    log_node_enter("respond", state=state)
    trace_label = format_router_trace_label(state)
    system_instruction, tools = resolve_system_instruction(state)
    temperature = _respond_temperature(state)
    writer = get_stream_writer()
    gemini_contents = build_gemini_contents(state.get("messages", []))
    confirmation = (state.get("scrap_confirmation_text") or "").strip()
    loop_count = int(state.get("respond_loop_count") or 0)

    writer(status_event(MSG_RESPOND_GENERATING, phase="respond"))

    writer({"event": "token", "content": SCRAP_FOLLOWUP_BRIDGE})

    try:
        summary_text, _ = await _stream_gemini_text(
            system_instruction=system_instruction,
            gemini_contents=gemini_contents,
            tools=tools,
            temperature=temperature,
            writer=writer,
            allow_scrap_tool=False,
        )
    except Exception:
        logger.exception(
            "Archiver respond follow-up stream failed label=%s", trace_label
        )
        writer({"event": "token", "content": STREAM_ERROR_MESSAGE})
        log_respond_result(
            route=trace_label,
            response_chars=len(STREAM_ERROR_MESSAGE),
            temperature=temperature,
            has_error=True,
        )
        return _error_return(
            trace_label=trace_label,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    combined = f"{confirmation}{SCRAP_FOLLOWUP_BRIDGE}{summary_text}".strip()
    log_respond_result(
        route=trace_label,
        response_chars=len(combined),
        temperature=temperature,
        has_error=False,
    )
    return {
        "final_response": combined,
        "system_instruction": system_instruction,
        "messages": [AIMessage(content=combined)],
        "pending_followup_summary": False,
        "respond_loop_count": loop_count + 1,
        "current_step": "respond",
    }


async def _respond_primary(state: ArchiverState) -> dict[str, Any]:
    """1차 respond — 일반 답변 또는 scrap_current_page 도구 트리거."""
    log_node_enter("respond", state=state)
    trace_label = format_router_trace_label(state)
    system_instruction, tools = resolve_system_instruction(state)
    temperature = _respond_temperature(state)
    writer = get_stream_writer()
    gemini_contents = build_gemini_contents(state.get("messages", []))
    loop_count = int(state.get("respond_loop_count") or 0)

    writer(status_event(MSG_RESPOND_GENERATING, phase="respond"))

    try:
        final_text, scrap_tool_args = await _stream_gemini_text(
            system_instruction=system_instruction,
            gemini_contents=gemini_contents,
            tools=tools,
            temperature=temperature,
            writer=writer,
            allow_scrap_tool=True,
        )
    except Exception:
        logger.exception("Archiver respond stream failed label=%s", trace_label)
        writer({"event": "token", "content": STREAM_ERROR_MESSAGE})
        log_respond_result(
            route=trace_label,
            response_chars=len(STREAM_ERROR_MESSAGE),
            temperature=temperature,
            has_error=True,
        )
        return _error_return(
            trace_label=trace_label,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    if scrap_tool_args is not None:
        custom_category = _user_specified_category_from_tool_args(scrap_tool_args)
        schedule_followup = should_schedule_scrap_followup_summary(state)
        writer(trigger_web_scrap_event(custom_category=custom_category))
        writer({"event": "token", "content": SCRAP_CONFIRMATION_MESSAGE})
        log_respond_result(
            route=trace_label,
            response_chars=len(SCRAP_CONFIRMATION_MESSAGE),
            temperature=temperature,
            has_error=False,
        )
        result: dict[str, Any] = {
            "final_response": SCRAP_CONFIRMATION_MESSAGE,
            "system_instruction": system_instruction,
            "scrap_confirmation_text": SCRAP_CONFIRMATION_MESSAGE,
            "executed_respond_tools": [SCRAP_CURRENT_PAGE_TOOL_NAME],
            "respond_loop_count": loop_count + 1,
            "pending_followup_summary": schedule_followup,
            "current_step": "respond",
        }
        if not schedule_followup:
            result["messages"] = [AIMessage(content=SCRAP_CONFIRMATION_MESSAGE)]
        return result

    log_respond_result(
        route=trace_label,
        response_chars=len(final_text),
        temperature=temperature,
        has_error=False,
    )
    return {
        "final_response": final_text,
        "system_instruction": system_instruction,
        "messages": [AIMessage(content=final_text)],
        "respond_loop_count": loop_count + 1,
        "current_step": "respond",
    }


async def respond(state: ArchiverState) -> dict[str, Any]:
    """최종 답변을 Gemini 스트리밍으로 생성하고 custom stream 이벤트를 방출한다."""
    if is_scrap_followup_pass(state):
        return await _respond_scrap_followup_summary(state)
    return await _respond_primary(state)
