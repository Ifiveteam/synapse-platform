"""classify 스텝 — 사용자 질문 의도를 4방향 경로로 분류한다."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types
from langgraph.config import get_stream_writer

from app.agents.archiver.constants import CLASSIFY_TEMPERATURE
from app.agents.archiver.gemini import GEMINI_MODEL, get_client, invoke_structured_safe
from app.agents.archiver.prompts import build_router_prompt
from app.agents.archiver.router_heuristics import detect_route_heuristic
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.trace import log_node_enter, log_router_result
from app.agents.archiver.types import (
    ArchiverRoute,
    ArchiverState,
    RouterDecision,
    parse_archiver_route,
)

logger = logging.getLogger(__name__)


async def classify_archiver_route(user_message: str) -> tuple[ArchiverRoute, str | None]:
    """규칙 → Structured Output → 텍스트 파싱 순으로 BASIC/RAG/SEARCH/GENERAL을 반환한다."""
    message = user_message.strip()
    if not message:
        return ArchiverRoute.GENERAL, None

    heuristic = detect_route_heuristic(message)
    if heuristic is not None:
        return heuristic, f"heuristic:{heuristic.value}"

    try:
        decision = await invoke_structured_safe(
            system_instruction=build_router_prompt(message),
            user_content=message,
            schema=RouterDecision,
            temperature=CLASSIFY_TEMPERATURE,
        )
        if decision is not None:
            route = ArchiverRoute(decision.route)
            return route, decision.route

        response = await get_client().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=build_router_prompt(message),
                temperature=CLASSIFY_TEMPERATURE,
                max_output_tokens=8,
            ),
        )
        raw_route = (response.text or "").strip()
        route = parse_archiver_route(raw_route)
        return route, raw_route
    except Exception:
        logger.exception("Archiver classify step failed")
        return ArchiverRoute.GENERAL, None


async def classify(state: ArchiverState) -> dict[str, Any]:
    """route 필드를 설정하고 SSE 상태 이벤트를 방출한다."""
    log_node_enter("router", state=state)
    user_message = latest_user_message(state)
    route, raw_route = await classify_archiver_route(user_message)

    log_router_result(route=route.value, raw_route=raw_route)

    writer = get_stream_writer()
    if route == ArchiverRoute.GENERAL:
        writer(
            {
                "event": "status",
                "content": (
                    f"💬 [Router] `{route.value}` 일상 대화 — "
                    "수집·평가 단계를 건너뛰고 답변을 생성합니다...\n\n"
                ),
            }
        )
    else:
        writer(
            {
                "event": "status",
                "content": (
                    f"🔀 [Router] 처리 경로를 `{route.value}`(으)로 분류했습니다...\n\n"
                ),
            }
        )

    return {
        "route": route,
        "current_step": "router",
    }
