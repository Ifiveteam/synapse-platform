"""Archiver 라우팅·루프 분기 trace."""

from __future__ import annotations

from app.agents.archiver.observability import log_event
from app.agents.archiver.trace._common import logger
from app.agents.archiver.types import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
    Evaluation,
)


def log_router_branch(*, route: str, next_node: str) -> None:
    if next_node == "respond" and route == "GENERAL":
        reason = "GENERAL fast-path — 수집·evaluator 생략"
    elif next_node == "search" and route == "SEARCH":
        reason = "SEARCH 경로 — search 파이프라인 진입"
    elif next_node == "collect":
        reason = f"{route} 경로 — collect 수집 파이프라인 진입"
    else:
        reason = f"{route} 경로 — {next_node} 진입"
    log_event("router.branch", route=route, next_node=next_node, reason=reason)
    logger.info("  ┌─ 🔀 Router 조건부 분기")
    logger.info("  │ route      : %s", route)
    logger.info("  │ 다음 노드  : %s", next_node)
    logger.info("  │ 분기 사유  : %s", reason)
    logger.info("  └─ Router 분기 완료")


def log_evaluator_branch(
    *,
    evaluation: Evaluation,
    next_node: str,
    search_attempts: int,
    retrieval_attempts: int,
) -> None:
    if evaluation.is_sufficient:
        branch_reason = f"AI 채점 {evaluation.score}점 — 근거 충분"
    elif next_node == "search":
        branch_reason = (
            f"AI 권장 search — 역주행 (시도 {search_attempts + 1}/{MAX_SEARCH_ATTEMPTS})"
        )
    elif next_node == "collect":
        branch_reason = (
            f"AI 권장 collect — 역주행 (시도 {retrieval_attempts + 1}/{MAX_RETRIEVAL_ATTEMPTS})"
        )
    else:
        branch_reason = (
            f"루프 한도 또는 best-effort — search={search_attempts}, rag={retrieval_attempts}"
        )

    log_event(
        "evaluator.branch",
        eval_score=evaluation.score,
        is_sufficient=evaluation.is_sufficient,
        recommended_action=evaluation.recommended_action,
        next_node=next_node,
        search_loops=search_attempts,
        reason=branch_reason,
    )
    logger.info("  ┌─ 🔀 Evaluator 조건부 분기 (LLM Structured Output)")
    logger.info("  │ AI 채점     : %s / 100", evaluation.score)
    logger.info("  │ 충분성      : %s", "✅ 충분" if evaluation.is_sufficient else "❌ 불충분")
    logger.info("  │ 권장 액션   : %s", evaluation.recommended_action)
    logger.info("  │ search      : %s / %s회", search_attempts, MAX_SEARCH_ATTEMPTS)
    logger.info("  │ collect     : %s / %s회", retrieval_attempts, MAX_RETRIEVAL_ATTEMPTS)
    logger.info("  │ 판단 근거   : %s", evaluation.reason or "(없음)")
    logger.info("  │ 다음 노드   : %s", next_node)
    logger.info("  │ 분기 사유   : %s", branch_reason)
    logger.info("  └─ Evaluator 분기 완료")
