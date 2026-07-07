"""finalize 노드 — 대화를 마무리하며 완성된 이상향을 설명하고 complete 이벤트로
최종 성향·도메인(+8/13·페르소나)을 방출한다. (프론트가 확정 버튼을 활성화)"""

from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from app.agents.navigator.constants import CHAT_TEMPERATURE, STREAM_ERROR_MESSAGE
from app.agents.navigator.llm import GEMINI_MODEL, get_client
from app.agents.navigator.nodes._common import to_gemini_contents
from app.agents.navigator.prompts.chat import build_finalize_prompt
from app.agents.navigator.state import NavigatorState

logger = logging.getLogger(__name__)


def _complete_payload(state: NavigatorState) -> str:
    return json.dumps(
        {
            "disposition": state.get("working_disposition") or {},
            "interest": state.get("working_interest") or {},
            "behavior": state.get("working_ideal") or {},
            "values_temperament": state.get("working_values") or {},
            "persona_label": state.get("persona_label") or "",
            "reasoning": state.get("ideal_reasoning") or "",
            "keywords": state.get("working_keywords") or [],
            "ideal_type": "CUSTOM",
        },
        ensure_ascii=False,
    )


async def finalize(state: NavigatorState) -> dict[str, Any]:
    """마무리 멘트 스트리밍 + complete 이벤트(최종 이상향)."""
    writer = get_stream_writer()
    system_instruction = build_finalize_prompt(state)
    contents = to_gemini_contents(state.get("messages", []))

    writer({"event": "status", "content": "✨ [Navigator] 이상향을 완성합니다...\n\n"})

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
        logger.exception("Navigator finalize stream failed")
        writer({"event": "token", "content": STREAM_ERROR_MESSAGE})

    # 대화 멘트가 실패해도 완성된 이상향은 넘겨준다.
    writer({"event": "complete", "content": _complete_payload(state)})

    final_response = "".join(chunks)
    return {
        "final_response": final_response,
        "messages": [AIMessage(content=final_response)] if final_response else [],
        "current_step": "finalize",
    }
