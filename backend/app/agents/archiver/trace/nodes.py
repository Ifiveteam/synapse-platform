"""Archiver 노드 실행 단계 trace."""

from __future__ import annotations

from app.agents.archiver.trace._common import logger, truncate
from app.agents.archiver.trace.observability import log_event
from app.agents.archiver.models import Evaluation


def log_router_result(*, route: str, raw_route: str | None = None) -> None:
    log_event("router.result", route=route, raw_route=raw_route)
    logger.info("  ┌─ 🔀 Router 분류 결과")
    if raw_route is not None:
        logger.info("  │ raw_output : %r", raw_route)
    logger.info("  │ resolved   : %s", route)
    logger.info("  └─ Router 완료")


def log_collect_result(
    *,
    route: str,
    rag_chars: int,
    context_body_chars: int,
    retrieval_attempts: int,
    rag_hit: bool,
) -> None:
    log_event(
        "collect.result",
        route=route,
        rag_chars=rag_chars,
        context_body_chars=context_body_chars,
        retrieval_attempts=retrieval_attempts,
        rag_hit=rag_hit,
    )
    logger.info("  ┌─ 📥 collect 수집 결과")
    logger.info("  │ route              : %s", route)
    logger.info("  │ retrieval_attempts : %s", retrieval_attempts)
    logger.info("  │ rag_data           : %s자 (hit=%s)", rag_chars, "✅" if rag_hit else "❌")
    logger.info("  │ context_body       : %s자", context_body_chars)
    logger.info("  └─ collect 완료")


def log_search_payload(*, search_data: str, search_attempts: int, is_loop: bool) -> None:
    log_event(
        "search.result",
        search_chars=len(search_data),
        search_loops=search_attempts,
        is_loop=is_loop,
    )
    loop_label = "역주행 재시도" if is_loop else "최초 실행"
    logger.info("  ┌─ 🔍 search 수집 결과 (%s)", loop_label)
    logger.info("  │ search_attempts : %s", search_attempts)
    logger.info("  │ search_data     : %s자", len(search_data))
    if search_data:
        for line in truncate(search_data, limit=300).splitlines():
            logger.info("  │ %s", line)
    logger.info("  └─ search 완료")


def log_evaluation_result(*, evaluation: Evaluation, source: str = "llm") -> None:
    log_event(
        "evaluator.result",
        source=source,
        is_sufficient=evaluation.is_sufficient,
        recommended_action=evaluation.recommended_action,
        reason=evaluation.reason,
    )
    logger.info("  ┌─ ⚖️ Evaluator AI 채점 (%s)", source)
    logger.info("  │ is_sufficient     : %s", evaluation.is_sufficient)
    logger.info("  │ recommended_action: %s", evaluation.recommended_action)
    for line in truncate(evaluation.reason, limit=500).splitlines():
        logger.info("  │ %s", line)
    logger.info("  └─ Evaluator 채점 완료")


def log_respond_result(
    *,
    route: str,
    response_chars: int,
    temperature: float,
    has_error: bool,
) -> None:
    log_event(
        "respond.result",
        route=route,
        response_chars=response_chars,
        temperature=temperature,
        has_error=has_error,
    )
    logger.info("  ┌─ ✨ Respond 최종 생성")
    logger.info("  │ route         : %s", route)
    logger.info("  │ temperature   : %s", temperature)
    logger.info("  │ response      : %s자", response_chars)
    logger.info("  │ status        : %s", "❌ 오류" if has_error else "✅ 성공")
    logger.info("  └─ Respond 완료")
