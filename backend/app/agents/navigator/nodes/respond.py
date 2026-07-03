"""ask 노드 — 취향을 더 알아내는 자연스러운 질문 하나를 스트리밍 생성한다."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from app.agents.navigator.constants import CHAT_TEMPERATURE, STREAM_ERROR_MESSAGE
from app.agents.navigator.llm import GEMINI_MODEL, get_client
from app.agents.navigator.nodes._common import to_gemini_contents
from app.agents.navigator.prompts.chat import build_ask_prompt
from app.agents.navigator.state import NavigatorState

logger = logging.getLogger(__name__)


async def ask(state: NavigatorState) -> dict[str, Any]:
    """Gemini 스트리밍으로 취향 질문을 생성하고 token 이벤트를 방출한다."""
    writer = get_stream_writer()
    system_instruction = build_ask_prompt(state)
    contents = to_gemini_contents(state.get("messages", []))

    writer({"event": "status", "content": "💬 [Navigator] 질문을 준비합니다...\n\n"})

    chunks: list[str] = []
    try:
        stream = await get_client().aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=CHAT_TEMPERATURE,
            ),
        )
        async for chunk in stream:
            if chunk.text:
                chunks.append(chunk.text)
                writer({"event": "token", "content": chunk.text})
    except Exception:
        logger.exception("Navigator ask stream failed")
        writer({"event": "token", "content": STREAM_ERROR_MESSAGE})
        return {
            "final_response": STREAM_ERROR_MESSAGE,
            "current_step": "ask",
            "error": STREAM_ERROR_MESSAGE,
        }

    final_response = "".join(chunks)
    return {
        "final_response": final_response,
        "messages": [AIMessage(content=final_response)],
        "current_step": "ask",
    }
