"""evaluate 스텝 — Gemini Structured Output 기반 지능형 근거 채점."""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.constants import EVALUATE_TEMPERATURE
from app.agents.archiver.gemini import invoke_structured_safe
from app.agents.archiver.prompts.evaluator_prompt import build_evaluator_prompt
from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.trace import log_evaluation_result, log_node_enter
from app.agents.archiver.types import ArchiverState, Evaluation, resolve_route


async def evaluate_with_llm(state: ArchiverState) -> tuple[Evaluation, str]:
    """수집 근거를 Gemini Structured Output으로 채점한다."""
    user_message = latest_user_message(state)
    route = resolve_route(state)

    system_instruction, user_content = build_evaluator_prompt(
        route=route,
        user_message=user_message,
        context_title=state.get("context_title", ""),
        context_url=state.get("context_url", ""),
        context_body=state.get("context_body", "") or "",
        rag_data=state.get("rag_data", "") or "",
        search_data=state.get("search_data", "") or "",
        search_attempts=state.get("search_attempts", 0),
        retrieval_attempts=state.get("retrieval_attempts", 0),
    )

    llm_result = await invoke_structured_safe(
        system_instruction=system_instruction,
        user_content=user_content,
        schema=Evaluation,
        temperature=EVALUATE_TEMPERATURE,
    )

    if llm_result is None:
        return Evaluation.fallback(state=state), "fallback"

    return llm_result, "llm"


async def evaluate(state: ArchiverState) -> dict[str, Any]:
    """수집 데이터를 LLM으로 평가하고 evaluation_result를 기록한다."""
    log_node_enter("evaluator", state=state)
    evaluation, source = await evaluate_with_llm(state)
    log_evaluation_result(evaluation=evaluation, source=source)

    writer = get_stream_writer()
    writer(
        {
            "event": "status",
            "content": (
                f"⚖️ [Evaluator] AI 채점 — 충분성={evaluation.is_sufficient} "
                f"(score={evaluation.score}) — {evaluation.reason}\n\n"
            ),
        }
    )

    return {
        "evaluation_result": evaluation.to_state_dict(),
        "current_step": "evaluator",
    }
