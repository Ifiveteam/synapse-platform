"""search 스텝 — Google Search Tool 기반 외부 정보 수집."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langgraph.config import get_stream_writer

from app.agents.archiver.constants import SEARCH_TEMPERATURE
from app.agents.archiver.gemini import GEMINI_MODEL, get_client
from app.agents.archiver.prompts import build_search_route_instruction
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.trace import log_node_enter, log_search_payload
from app.agents.archiver.types import ArchiverState, Evaluation

logger = logging.getLogger(__name__)

_GOOGLE_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


async def search(state: ArchiverState) -> dict[str, Any]:
    """SEARCH 경로 또는 evaluator 역주행 시 Google Search로 search_data를 채운다."""
    log_node_enter("search", state=state)

    user_message = latest_user_message(state)
    prior_attempts = state.get("search_attempts", 0)
    search_attempts = prior_attempts + 1
    is_loop = prior_attempts > 0 or Evaluation.from_state(state) is not None

    writer = get_stream_writer()
    writer(
        {
            "event": "status",
            "content": (
                f"🔍 [Search] 실시간 구글 검색을 수행합니다 "
                f"(시도 {search_attempts})...\n\n"
            ),
        }
    )

    system_instruction = build_search_route_instruction(
        context_title=state.get("context_title"),
        context_url=state.get("context_url"),
    )

    try:
        response = await get_client().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[_GOOGLE_SEARCH_TOOL],
                temperature=SEARCH_TEMPERATURE,
            ),
        )
        search_payload = (response.text or "").strip()
    except Exception:
        logger.exception("Archiver search step failed")
        search_payload = ""

    log_search_payload(
        search_data=search_payload,
        search_attempts=search_attempts,
        is_loop=is_loop,
    )

    return {
        "search_data": search_payload,
        "search_attempts": search_attempts,
        "current_step": "search",
    }
