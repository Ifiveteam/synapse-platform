"""Archiver LangGraph 조건부 분기 — 다중 엔진 fan-out / fan-in 및 evaluator 루프."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from app.agents.archiver.prompts.evaluator_prompt import ACTION_ENGINE_MAP
from app.agents.archiver.models import (
    ArchiverState,
    normalize_target_engines,
    remaining_engines,
)
from app.agents.archiver.steps.scraper import is_usable_context_body
from app.agents.archiver.trace import log_evaluator_branch, log_router_branch
from app.agents.archiver.models import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
    ArchiverRoute,
    Evaluation,
    resolve_route,
)
from app.agents.archiver.models import COLLECT_NODE, RAG_NODE, SEARCH_NODE

RouteAfterRouter = (
    Literal["respond", "need_dom", "collect_node", "rag_node", "search_node"]
    | list[Send]
)
RouteAfterEvaluator = (
    Literal["respond", "collect_node", "rag_node", "search_node"] | list[Send]
)


def needs_dom_collection(state: ArchiverState) -> bool:
    """collect_node가 필요하지만 클라이언트 DOM이 아직 없을 때."""
    if COLLECT_NODE not in normalize_target_engines(state.get("target_engines")):
        return False
    existing_body = (state.get("context_dom") or state.get("context_body") or "").strip()
    dom_continuation = state.get("dom_continuation", False)
    return not is_usable_context_body(existing_body) and not dom_continuation


def _fan_out_sends(state: ArchiverState, engines: list[str]) -> list[Send]:
    """지정 엔진에 대해 LangGraph Send fan-out 리스트를 생성한다."""
    return [Send(engine, state) for engine in engines]


def _filter_by_attempt_budget(state: ArchiverState, engines: list[str]) -> list[str]:
    """시도 한도를 초과한 엔진을 제외한다."""
    search_attempts = state.get("search_attempts", 0)
    retrieval_attempts = state.get("retrieval_attempts", 0)
    allowed: list[str] = []
    for engine in engines:
        if engine == SEARCH_NODE and search_attempts >= MAX_SEARCH_ATTEMPTS:
            continue
        if engine == RAG_NODE and retrieval_attempts >= MAX_RETRIEVAL_ATTEMPTS:
            continue
        allowed.append(engine)
    return allowed


def _engines_for_recommended_action(
    action: str,
    pending: list[str],
) -> list[str]:
    """evaluator recommended_action을 pending 엔진 목록에 매핑한다."""
    if action in {"none", "respond"}:
        return []
    engine = ACTION_ENGINE_MAP.get(action)
    if engine:
        matched = [e for e in pending if e == engine]
        if matched:
            return matched
    return pending


def _is_general_fast_path_state(state: ArchiverState) -> bool:
    """GENERAL 프리패스 — 수집·evaluator 파이프라인 생략."""
    if state.get("is_general"):
        return True
    route = resolve_route(state)
    targets = normalize_target_engines(state.get("target_engines"))
    return route == ArchiverRoute.GENERAL or not targets


def route_after_router(state: ArchiverState) -> RouteAfterRouter:
    """router 이후 GENERAL→respond 프리패스, need_dom, 또는 1차 병렬 fan-out."""
    if _is_general_fast_path_state(state):
        route = resolve_route(state)
        log_router_branch(route=route.value, next_node="respond", targets=[])
        return "respond"

    route = resolve_route(state)
    targets = normalize_target_engines(state.get("target_engines"))

    if needs_dom_collection(state):
        log_router_branch(route=route.value, next_node="need_dom", targets=targets)
        return "need_dom"

    sends = _fan_out_sends(state, targets)
    log_router_branch(route=route.value, next_node="parallel_fan_out", targets=targets)
    return sends


def route_after_evaluator(state: ArchiverState) -> RouteAfterEvaluator:
    """통합 평가 후 respond 또는 미실행 엔진으로 선택적 역주행 fan-out."""
    evaluation = Evaluation.from_state(state)
    search_attempts = state.get("search_attempts", 0)
    retrieval_attempts = state.get("retrieval_attempts", 0)

    if evaluation is None or evaluation.is_sufficient:
        next_node: RouteAfterEvaluator = "respond"
        if evaluation is not None:
            log_evaluator_branch(
                evaluation=evaluation,
                next_node=next_node,
                search_attempts=search_attempts,
                retrieval_attempts=retrieval_attempts,
                remaining=[],
            )
        return next_node

    action = evaluation.normalized_action()
    if action == "none":
        log_evaluator_branch(
            evaluation=evaluation,
            next_node="respond",
            search_attempts=search_attempts,
            retrieval_attempts=retrieval_attempts,
            remaining=[],
        )
        return "respond"

    pending = remaining_engines(state)
    pending = _filter_by_attempt_budget(state, pending)

    if not pending:
        log_evaluator_branch(
            evaluation=evaluation,
            next_node="respond",
            search_attempts=search_attempts,
            retrieval_attempts=retrieval_attempts,
            remaining=[],
        )
        return "respond"

    retry_targets = _engines_for_recommended_action(action, pending)
    if not retry_targets:
        log_evaluator_branch(
            evaluation=evaluation,
            next_node="respond",
            search_attempts=search_attempts,
            retrieval_attempts=retrieval_attempts,
            remaining=[],
        )
        return "respond"

    sends = _fan_out_sends(state, retry_targets)
    log_evaluator_branch(
        evaluation=evaluation,
        next_node="parallel_fan_out",
        search_attempts=search_attempts,
        retrieval_attempts=retrieval_attempts,
        remaining=retry_targets,
    )
    return sends
