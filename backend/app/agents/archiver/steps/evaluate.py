"""evaluate 스텝 — Gemini Structured Output 기반 다중 엔진 통합 근거 채점."""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.core.constants import (
    EVALUATE_TEMPERATURE,
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
)
from app.agents.archiver.core.gemini import invoke_structured_safe
from app.agents.archiver.prompts.evaluator_prompt import (
    ACTION_ENGINE_MAP,
    build_evaluator_prompt,
)
from app.agents.archiver.protocols.stream_status import evaluator_message, status_event
from app.agents.archiver.models import (
    normalize_target_engines,
    remaining_engines,
)
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.trace import log_evaluation_result, log_node_enter
from app.agents.archiver.models import (
    ArchiverState,
    Evaluation,
    get_context_dom,
    get_context_rag,
    get_context_search,
    resolve_route,
)


def _sanitize_evaluation(evaluation: Evaluation, state: ArchiverState) -> Evaluation:
    """LLM이 이미 실행된 엔진을 추천한 경우 pending 기준으로 교정한다."""
    pending = remaining_engines(state)
    action = evaluation.normalized_action()

    if evaluation.is_sufficient:
        if action != "none":
            return evaluation.model_copy(update={"recommended_action": "none"})
        return evaluation

    if action == "none" or not pending:
        if not pending:
            return evaluation.model_copy(
                update={
                    "recommended_action": "none",
                    "reason": evaluation.reason
                    + " (추가 수집 가능 엔진 없음 — best-effort 진행)",
                },
            )
        return evaluation

    engine = ACTION_ENGINE_MAP.get(action)
    if engine and engine not in pending:
        fallback_action = next(
            (a for a, eng in ACTION_ENGINE_MAP.items() if eng in pending),
            "none",
        )
        return evaluation.model_copy(
            update={
                "recommended_action": fallback_action,
                "reason": evaluation.reason
                + f" (교정: {action} 불가 → {fallback_action})",
            },
        )
    return evaluation


async def _evaluate_with_llm(state: ArchiverState) -> tuple[Evaluation, str]:
    """수집 근거를 Gemini Structured Output으로 채점한다 (evaluate 전용)."""
    user_message = latest_user_message(state)
    route = resolve_route(state)
    executed = list(state.get("executed_steps") or [])
    pending = remaining_engines(state)

    system_instruction, user_content = build_evaluator_prompt(
        route=route,
        user_message=user_message,
        context_title=state.get("context_title", ""),
        context_url=state.get("context_url", ""),
        context_dom=get_context_dom(state),
        context_rag=get_context_rag(state),
        context_search=get_context_search(state),
        target_engines=normalize_target_engines(state.get("target_engines")),
        executed_steps=executed,
        pending_engines=pending,
        search_attempts=state.get("search_attempts", 0),
        retrieval_attempts=state.get("retrieval_attempts", 0),
        max_search_attempts=MAX_SEARCH_ATTEMPTS,
        max_retrieval_attempts=MAX_RETRIEVAL_ATTEMPTS,
    )

    llm_result = await invoke_structured_safe(
        system_instruction=system_instruction,
        user_content=user_content,
        schema=Evaluation,
        temperature=EVALUATE_TEMPERATURE,
    )

    if llm_result is None:
        return Evaluation.fallback(state=state), "fallback"

    return _sanitize_evaluation(llm_result, state), "llm"


async def evaluate(state: ArchiverState) -> dict[str, Any]:
    """수집 데이터를 LLM으로 평가하고 evaluation_result를 기록한다."""
    log_node_enter("evaluator", state=state)
    evaluation, source = await _evaluate_with_llm(state)
    log_evaluation_result(evaluation=evaluation, source=source)

    writer = get_stream_writer()
    writer(status_event(evaluator_message(evaluation)))

    return {
        "evaluation_result": evaluation.to_state_dict(),
        "current_step": "evaluator",
    }
