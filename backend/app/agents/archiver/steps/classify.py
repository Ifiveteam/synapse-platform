"""classify 스텝 — 경량 LLM 라우터로 1차 병렬 수집 엔진을 선별한다."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.core.constants import (
    CLASSIFY_MAX_OUTPUT_TOKENS,
    CLASSIFY_MODEL,
    CLASSIFY_TEMPERATURE,
)
from app.agents.archiver.core.gemini import invoke_structured_safe
from app.agents.archiver.prompts import build_router_prompt
from app.agents.archiver.models import (
    ArchiverRoute,
    ArchiverState,
    RouterTargets,
    derive_route_from_targets,
    normalize_target_engines,
)
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.protocols.stream_status import (
    MSG_ROUTER_GENERAL,
    router_parallel_message,
    status_event,
)
from app.agents.archiver.trace import log_node_enter, log_router_result

logger = logging.getLogger(__name__)


def _general_result(raw_detail: str | None) -> tuple[list[str], ArchiverRoute, str | None]:
    return [], ArchiverRoute.GENERAL, raw_detail


def _normalize_router_decision(decision: RouterTargets) -> RouterTargets:
    """LLM 출력 불일치(is_general ↔ targets)를 스키마 규칙에 맞게 정규화한다."""
    if decision.is_general:
        return RouterTargets(targets=[], is_general=True)
    targets = normalize_target_engines(list(decision.targets))
    if not targets:
        return RouterTargets(targets=[], is_general=True)
    return RouterTargets(targets=targets, is_general=False)


def _router_llm_fallback(message: str) -> RouterTargets:
    """Gemini 빈 응답·예외 시 라우터 전용 안전 기본값."""
    stripped = message.strip()
    if not stripped:
        return RouterTargets(targets=[], is_general=True)
    return RouterTargets(targets=[], is_general=False)


async def _invoke_router_llm(
    *,
    router_prompt: str,
    message: str,
) -> RouterTargets:
    """라우터 전용 경량 Flash 모델로 구조화 분류만 수행한다."""
    result = await invoke_structured_safe(
        system_instruction=router_prompt,
        user_content=message,
        schema=RouterTargets,
        temperature=CLASSIFY_TEMPERATURE,
        model=CLASSIFY_MODEL,
        max_output_tokens=CLASSIFY_MAX_OUTPUT_TOKENS,
        fallback_factory=lambda: _router_llm_fallback(message),
    )
    if result is None:
        return _router_llm_fallback(message)
    return _normalize_router_decision(result)


async def _resolve_router_targets(
    user_message: str,
    *,
    context_url: str = "",
    context_title: str = "",
) -> tuple[list[str], ArchiverRoute, str | None, bool]:
    """경량 LLM으로 1차 병렬 실행 엔진·route·is_general을 반환한다 (classify 전용)."""
    message = user_message.strip()
    if not message:
        return [], ArchiverRoute.GENERAL, "preflight:empty", True

    router_prompt = build_router_prompt(
        message,
        context_url=context_url,
        context_title=context_title,
    )
    decision = await _invoke_router_llm(router_prompt=router_prompt, message=message)
    raw_detail = f"llm:{','.join(decision.targets) or 'general'}"

    if decision.is_general or not decision.targets:
        return (*_general_result(raw_detail), True)

    targets = normalize_target_engines(list(decision.targets))
    if not targets:
        return (*_general_result(raw_detail or "empty:general"), True)

    route = derive_route_from_targets(targets, is_general=False)
    return targets, route, raw_detail, False


async def classify(state: ArchiverState) -> dict[str, Any]:
    """target_engines·route·is_general을 설정하고 SSE 상태 이벤트를 방출한다."""
    log_node_enter("router", state=state)
    user_message = latest_user_message(state)
    targets, route, raw_detail, is_general = await _resolve_router_targets(
        user_message,
        context_url=state.get("context_url", ""),
        context_title=state.get("context_title", ""),
    )

    if is_general:
        targets = []
        route = ArchiverRoute.GENERAL

    targets = normalize_target_engines(targets)

    log_router_result(route=route.value, raw_route=raw_detail)

    writer = get_stream_writer()
    if is_general or route == ArchiverRoute.GENERAL or not targets:
        writer(status_event(MSG_ROUTER_GENERAL))
    else:
        writer(status_event(router_parallel_message(targets)))

    return {
        "route": route,
        "is_general": is_general,
        "target_engines": targets,
        "current_step": "router",
    }
