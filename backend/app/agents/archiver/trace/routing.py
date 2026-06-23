"""Archiver 라우팅·루프 분기 trace."""

from __future__ import annotations

from app.agents.archiver.trace.observability import log_event
from app.agents.archiver.trace._common import logger
from app.agents.archiver.models import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
    Evaluation,
)


def log_router_branch(
    *,
    route: str,
    next_node: str,
    targets: list[str] | None = None,
) -> None:
    target_list = targets or []
    if next_node == "respond" and route == "GENERAL":
        reason = "GENERAL fast-path — 수집·evaluator 생략"
    elif next_node == "need_dom":
        reason = f"DOM 선행 수집 필요 — targets={target_list}"
    elif next_node == "parallel_fan_out":
        reason = f"1차 병렬 fan-out — engines={target_list}"
    else:
        reason = f"{route} 경로 — {next_node} 진입"

    log_event(
        "router.branch",
        route=route,
        next_node=next_node,
        targets=target_list,
        reason=reason,
    )
    logger.info("  ┌─ 🔀 Router 조건부 분기")
    logger.info("  │ route      : %s", route)
    logger.info("  │ targets    : %s", target_list or "(없음)")
    logger.info("  │ 다음 노드  : %s", next_node)
    logger.info("  │ 분기 사유  : %s", reason)
    logger.info("  └─ Router 분기 완료")


def log_evaluator_branch(
    *,
    evaluation: Evaluation,
    next_node: str,
    search_attempts: int,
    retrieval_attempts: int,
    remaining: list[str] | None = None,
) -> None:
    pending = remaining or []
    if evaluation.is_sufficient:
        branch_reason = "AI 통합 심사 — 근거 충분"
    elif next_node == "parallel_fan_out":
        branch_reason = (
            f"AI 권장 {evaluation.recommended_action} — "
            f"미실행 엔진 병렬 역주행 {pending}"
        )
    elif next_node == "search_node":
        branch_reason = (
            f"AI 권장 search — 역주행 (시도 {search_attempts + 1}/{MAX_SEARCH_ATTEMPTS})"
        )
    elif next_node in {"collect_node", "rag_node"}:
        branch_reason = (
            f"AI 권장 {evaluation.recommended_action} — "
            f"역주행 (rag 시도 {retrieval_attempts + 1}/{MAX_RETRIEVAL_ATTEMPTS})"
        )
    else:
        branch_reason = (
            f"루프 한도 또는 best-effort — search={search_attempts}, rag={retrieval_attempts}"
        )

    log_event(
        "evaluator.branch",
        is_sufficient=evaluation.is_sufficient,
        recommended_action=evaluation.recommended_action,
        dom_verdict=evaluation.dom_verdict,
        rag_verdict=evaluation.rag_verdict,
        search_verdict=evaluation.search_verdict,
        next_node=next_node,
        search_loops=search_attempts,
        remaining_engines=pending,
        reason=branch_reason,
    )
    logger.info("  ┌─ 🔀 Evaluator 조건부 분기 (LLM Structured Output)")
    logger.info("  │ 충분성      : %s", "✅ 충분" if evaluation.is_sufficient else "❌ 불충분")
    logger.info("  │ 권장 액션   : %s", evaluation.recommended_action)
    logger.info(
        "  │ 소스 verdict: dom=%s | rag=%s | search=%s",
        evaluation.dom_verdict,
        evaluation.rag_verdict,
        evaluation.search_verdict,
    )
    logger.info("  │ search      : %s / %s회", search_attempts, MAX_SEARCH_ATTEMPTS)
    logger.info("  │ collect     : %s / %s회", retrieval_attempts, MAX_RETRIEVAL_ATTEMPTS)
    logger.info("  │ 남은 엔진   : %s", pending or "(없음)")
    logger.info("  │ 판단 근거   : %s", evaluation.reason or "(없음)")
    logger.info("  │ 다음 노드   : %s", next_node)
    logger.info("  │ 분기 사유   : %s", branch_reason)
    logger.info("  └─ Evaluator 분기 완료")
