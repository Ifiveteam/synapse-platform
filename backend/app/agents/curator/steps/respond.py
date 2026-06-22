"""respond 노드 — Gemini 스트리밍으로 최종 답변 생성."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer

from app.agents.curator.constants import GEMINI_MODEL, STREAM_ERROR_MESSAGE
from app.agents.curator.gemini import get_client
from app.agents.curator.types import CuratorRoute, CuratorState

logger = logging.getLogger(__name__)

_SYSTEM_BASE = """
당신은 Synapse 플랫폼의 오케스트레이터입니다.
유저의 YouTube 시청 데이터 기반 인사이트와 콘텐츠 탐색을 도와줍니다.
간결하고 핵심만 말하세요. 유저를 판단하지 마세요.
"""

_SYSTEM_MY_DATA = """
{base}

아래는 유저의 실제 데이터입니다. 이 데이터를 바탕으로 답변하세요.
데이터에 없는 내용은 지어내지 마세요.

<유저_데이터>
{{retrieval_context}}
</유저_데이터>
""".format(base=_SYSTEM_BASE)


def _build_contents(messages) -> list[dict]:
    contents = []
    for m in messages:
        role = "user" if isinstance(m, HumanMessage) else "model"
        contents.append({"role": role, "parts": [{"text": str(m.content)}]})
    return contents


async def respond(state: CuratorState) -> dict[str, Any]:
    writer = get_stream_writer()
    writer({"event": "status", "content": "✨ 답변을 생성하고 있습니다..."})

    route = state.get("route", CuratorRoute.GENERAL)

    if route == CuratorRoute.MY_DATA:
        context = state.get("retrieval_context", "(데이터 없음)")
        system_instruction = _SYSTEM_MY_DATA.replace("{{retrieval_context}}", context)
    else:
        system_instruction = _SYSTEM_BASE

    contents = _build_contents(state.get("messages", []))
    chunks: list[str] = []

    try:
        stream = await get_client().aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.5,
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
