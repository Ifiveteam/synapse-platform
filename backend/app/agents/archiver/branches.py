"""Archiver LangGraph 조건부 분기 — route별 수집 파이프라인 및 evaluator 루프."""

from __future__ import annotations

from typing import Literal

from app.agents.archiver.trace import log_evaluator_branch, log_router_branch
from app.agents.archiver.types import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
    ArchiverRoute,
    ArchiverState,
    Evaluation,
    resolve_route,
)

RouteAfterRouter = Literal["respond", "collect", "search"]
RouteAfterCollect = Literal["evaluator"]
RouteAfterEvaluator = Literal["search", "collect", "respond"]


def route_after_router(state: ArchiverState) -> RouteAfterRouter:
    """GENERAL⇒respond, SEARCH⇒search, RAG/BASIC⇒collect."""
    route = resolve_route(state)

    if route == ArchiverRoute.GENERAL:
        next_node: RouteAfterRouter = "respond"
    elif route == ArchiverRoute.SEARCH:
        next_node = "search"
    else:
        next_node = "collect"

    log_router_branch(route=route.value, next_node=next_node)
    return next_node


def route_after_collect(_state: ArchiverState) -> RouteAfterCollect:
    """collect 완료 후 evaluator로 진행."""
    return "evaluator"


def route_after_evaluator(state: ArchiverState) -> RouteAfterEvaluator:
    """LLM evaluator 채점 후 respond 진행 또는 수집 노드 역주행을 결정한다."""
    evaluation = Evaluation.from_state(state)
    search_attempts = state.get("search_attempts", 0)
    retrieval_attempts = state.get("retrieval_attempts", 0)

    if evaluation is None:
        next_node: RouteAfterEvaluator = "respond"
    elif evaluation.is_sufficient:
        next_node = "respond"
    elif (
        evaluation.recommended_action == "search"
        and search_attempts < MAX_SEARCH_ATTEMPTS
    ):
        next_node = "search"
    elif (
        evaluation.recommended_action == "collect"
        and retrieval_attempts < MAX_RETRIEVAL_ATTEMPTS
    ):
        next_node = "collect"
    else:
        next_node = "respond"

    if evaluation is not None:
        log_evaluator_branch(
            evaluation=evaluation,
            next_node=next_node,
            search_attempts=search_attempts,
            retrieval_attempts=retrieval_attempts,
        )
    return next_node
