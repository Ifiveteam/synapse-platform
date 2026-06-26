"""classify 스텝 — 경량 LLM 라우터로 1차 병렬 수집 엔진을 선별한다."""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.core.constants import (
    CLASSIFY_MAX_OUTPUT_TOKENS,
    CLASSIFY_MODEL,
    CLASSIFY_TEMPERATURE,
)
from app.agents.shared.gemini import invoke_structured_safe
from app.agents.archiver.prompts import build_router_prompt
from app.agents.archiver.utils.router_heuristics import (
    is_greeting_preflight,
    resolve_router_dialogue_context,
)
from app.agents.archiver.models import (
    ArchiverState,
    RouterTargets,
    format_router_trace_label,
    latest_user_message,
    normalize_target_engines,
)
from app.agents.archiver.protocols.stream_status import (
    MSG_ROUTER_GENERAL,
    router_parallel_message,
    status_event,
)
from app.agents.archiver.trace import log_node_enter, log_router_result


def normalize_router_decision(decision: RouterTargets) -> RouterTargets:
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
    return normalize_router_decision(result)


async def _resolve_router_targets(
    user_message: str,
    *,
    context_url: str = "",
    context_title: str = "",
    recent_dialogue: str | None = None,
) -> tuple[list[str], str | None, bool]:
    """preflight·LLM으로 1차 병렬 수집 엔진·is_general을 반환한다."""
    message = user_message.strip()
    if not message:
        return [], "preflight:empty", True
    if is_greeting_preflight(message):
        return [], "preflight:greeting", True

    router_prompt = build_router_prompt(
        context_url=context_url,
        context_title=context_title,
        recent_dialogue=recent_dialogue,
    )
    decision = await _invoke_router_llm(router_prompt=router_prompt, message=message)
    raw_detail = f"llm:{','.join(decision.targets) or 'general'}"

    if decision.is_general or not decision.targets:
        return [], raw_detail, True

    targets = normalize_target_engines(list(decision.targets))
    if not targets:
        return [], raw_detail or "empty:general", True

    return targets, raw_detail, False


async def classify(state: ArchiverState) -> dict[str, Any]:
    """target_engines·is_general을 설정하고 SSE 상태 이벤트를 방출한다."""
    log_node_enter("router", state=state)
    user_message = latest_user_message(state)
    targets, raw_detail, is_general = await _resolve_router_targets(
        user_message,
        context_url=state.get("context_url", ""),
        context_title=state.get("context_title", ""),
        recent_dialogue=resolve_router_dialogue_context(state, user_message),
    )

    if is_general:
        targets = []

    targets = normalize_target_engines(targets)
    trace_label = format_router_trace_label(is_general=is_general, target_engines=targets)

    log_router_result(route=trace_label, raw_route=raw_detail)

    writer = get_stream_writer()
    if is_general or not targets:
        writer(status_event(MSG_ROUTER_GENERAL, phase="router_general"))
    else:
        writer(
            status_event(
                router_parallel_message(targets),
                phase="router_parallel",
                engines=targets,
            )
        )

    return {
        "is_general": is_general,
        "target_engines": targets,
        "current_step": "router",
    }
