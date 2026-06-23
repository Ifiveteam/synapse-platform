"""search_node — Google Search Tool 기반 외부 정보를 context_search에 수집한다."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langgraph.config import get_stream_writer

from app.agents.archiver.core.constants import SEARCH_TEMPERATURE
from app.agents.archiver.utils.context_refine import (
    clean_context_title,
    clean_context_url,
    is_thin_context_body,
)
from app.agents.archiver.core.gemini import GEMINI_MODEL, get_client
from app.agents.archiver.prompts import build_search_collect_instruction
from app.agents.archiver.utils.search_query import build_search_user_content
from app.agents.archiver.models import SEARCH_NODE, ArchiverState
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.steps.scraper import is_usable_context_body
from app.agents.archiver.protocols.stream_status import (
    MSG_SEARCH_DEFAULT,
    MSG_SEARCH_TITLE_BASED,
    status_event,
)
from app.agents.archiver.core.tools import GOOGLE_SEARCH_TOOL
from app.agents.archiver.trace import log_node_enter, log_search_payload
from app.agents.archiver.models import (
    ArchiverRoute,
    Evaluation,
    get_context_dom,
    resolve_route,
)

logger = logging.getLogger(__name__)


async def search_node(state: ArchiverState) -> dict[str, Any]:
    """외부 웹 검색 API로 context_search를 채운다."""
    log_node_enter("search_node", state=state)

    user_message = latest_user_message(state)
    prior_search_data = (state.get("search_data") or "").strip()
    prior_attempts = state.get("search_attempts", 0)
    search_attempts = prior_attempts + 1
    is_loop = prior_attempts > 0 or Evaluation.from_state(state) is not None
    route = resolve_route(state)
    basic_dom_fallback = route == ArchiverRoute.BASIC and is_thin_context_body(
        get_context_dom(state),
    )

    writer = get_stream_writer()
    if basic_dom_fallback and search_attempts == 1:
        writer(status_event(MSG_SEARCH_TITLE_BASED))
    else:
        writer(status_event(MSG_SEARCH_DEFAULT))

    system_instruction = build_search_collect_instruction(
        context_title=clean_context_title(state.get("context_title"))
        or state.get("context_title"),
        context_url=clean_context_url(state.get("context_url"))
        or state.get("context_url"),
    )
    search_contents = build_search_user_content(state, user_message)

    search_payload = ""
    try:
        response = await get_client().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=search_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[GOOGLE_SEARCH_TOOL],
                temperature=SEARCH_TEMPERATURE,
            ),
        )
        search_payload = (response.text or "").strip()
    except Exception:
        logger.exception("Archiver search step failed")

    if not is_usable_context_body(search_payload) and prior_search_data:
        logger.info(
            "Archiver search miss or failure — keeping prior search_data (%s chars)",
            len(prior_search_data),
        )
        search_payload = prior_search_data

    log_search_payload(
        search_data=search_payload,
        search_attempts=search_attempts,
        is_loop=is_loop,
    )

    return {
        "context_search": search_payload,
        "search_data": search_payload,
        "search_attempts": search_attempts,
        "current_step": SEARCH_NODE,
        "executed_steps": [SEARCH_NODE],
    }
