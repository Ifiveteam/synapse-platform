"""respond 노드 — Gemini 스트리밍으로 최종 답변 생성."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer

from app.agents.curator.constants import (
    GEMINI_MODEL,
    RESPOND_MESSAGE_WINDOW,
    STREAM_ERROR_MESSAGE,
)
from app.agents.curator.gemini import get_client
from app.agents.curator.types import CuratorRoute, CuratorState

logger = logging.getLogger(__name__)

_SYSTEM_BASE = """
당신은 Synapse 플랫폼의 AI 큐레이터입니다.
유저의 YouTube 시청 데이터를 기반으로 인사이트를 분석하고, 콘텐츠 탐색과 시청 패턴 해석을 도와줍니다.

응답 원칙:
- 반드시 대화의 가장 마지막 유저 메시지에 응답하세요.
- 인사나 짧은 말에는 자연스럽게 짧게 답하세요. 설명을 늘어놓지 마세요.
- 마크다운을 적극 활용하세요 (볼드, 목록, 인용 등).
- 핵심만 간결하게 전달하고, 불필요한 서론·결론은 생략하세요.
- 유저를 판단하거나 평가하지 마세요. 데이터에서 발견된 패턴을 객관적으로 전달하세요.
- 데이터에 없는 내용은 절대 지어내지 마세요.
""".strip()


def _build_system_instruction(state: CuratorState) -> str:
    route = state.get("route", CuratorRoute.GENERAL)
    if route == CuratorRoute.MY_DATA:
        context = state.get("retrieval_context", "(데이터 없음)")
        return f"""{_SYSTEM_BASE}

---
아래는 유저의 실제 데이터입니다. 이 데이터를 바탕으로 답변하세요.
데이터에 없는 내용은 절대 지어내지 마세요.

<유저_데이터>
{context}
</유저_데이터>"""
    return _SYSTEM_BASE


def _build_contents(messages: list) -> list[dict]:
    contents = []
    for m in messages:
        role = "user" if isinstance(m, HumanMessage) else "model"
        contents.append({"role": role, "parts": [{"text": str(m.content)}]})
    return contents


async def respond(state: CuratorState) -> dict[str, Any]:
    writer = get_stream_writer()
    writer({"event": "status", "content": "✨ 답변을 생성하고 있습니다..."})

    system_instruction = _build_system_instruction(state)

    all_messages = state.get("messages", [])
    messages_to_use = all_messages[-RESPOND_MESSAGE_WINDOW:]
    contents = _build_contents(messages_to_use)

    chunks: list[str] = []

    try:
        stream = await get_client().aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6,
            ),
        )
        async for chunk in stream:
            if chunk.text:
                chunks.append(chunk.text)
                writer({"event": "token", "content": chunk.text})
    except Exception:
        logger.exception("Curator respond failed")
        writer({"event": "token", "content": STREAM_ERROR_MESSAGE})
        return {"final_response": STREAM_ERROR_MESSAGE, "error": STREAM_ERROR_MESSAGE}

    final_response = "".join(chunks)
    return {
        "final_response": final_response,
        "messages": [AIMessage(content=final_response)],
    }
