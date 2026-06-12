"""Aggregator Critique 루프 라우팅 및 상태 패치."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.types import Send

from app.agents.aggregator.state import (
    MAX_REVIEW_ATTEMPTS,
    REVIEW_PASS_THRESHOLD,
    AggregatorState,
)
from app.agents.aggregator.sub_agent.schemas import RevisionTarget, VerificationResult
from app.agents.aggregator.trace import log_route_decision

RouteAfterVerifyReturn = (
    Literal["__end__", "generate_report", "culture_analysis", "market_analysis"]
    | list[Send]
)


def build_verification_state_patch(
    result: VerificationResult,
    *,
    review_count: int,
) -> dict[str, Any]:
    """Pydantic 검수 결과를 AggregatorState에 안전·결정론적으로 반영할 패치를 생성한다."""
    normalized = VerificationResult.model_validate(result.model_dump())
    revision_target = normalized.resolve_revision_target()

    return {
        "verification_score": normalized.verification_score,
        "critique_feedback": normalized.critique_feedback,
        "is_template_valid": normalized.is_template_valid,
        "revision_target": revision_target,
        "review_count": review_count,
    }


def should_end_workflow(state: AggregatorState) -> bool:
    score = state.get("verification_score", 0)
    review_count = state.get("review_count", 0)
    return score >= REVIEW_PASS_THRESHOLD or review_count >= MAX_REVIEW_ATTEMPTS


def resolve_retry_destination(state: AggregatorState) -> RevisionTarget:
    target = state.get("revision_target", "generate_report")
    if target in (
        "generate_report",
        "culture_analysis",
        "market_analysis",
        "both_analyses",
    ):
        return target  # type: ignore[return-value]
    return "generate_report"


def route_after_verify(state: AggregatorState) -> RouteAfterVerifyReturn:
    """검수 결과에 따라 종료·마스터 재융합·서브 에이전트 역주행을 결정한다."""
    score = state.get("verification_score", 0)
    review_count = state.get("review_count", 0)

    if should_end_workflow(state):
        log_route_decision(
            score=score,
            review_count=review_count,
            pass_threshold=REVIEW_PASS_THRESHOLD,
            max_attempts=MAX_REVIEW_ATTEMPTS,
            next_node="__end__",
            revision_target=state.get("revision_target"),
        )
        return "__end__"

    destination = resolve_retry_destination(state)

    if destination == "both_analyses":
        log_route_decision(
            score=score,
            review_count=review_count,
            pass_threshold=REVIEW_PASS_THRESHOLD,
            max_attempts=MAX_REVIEW_ATTEMPTS,
            next_node="culture_analysis + market_analysis (병렬)",
            revision_target=destination,
        )
        return [
            Send("culture_analysis", state),
            Send("market_analysis", state),
        ]

    log_route_decision(
        score=score,
        review_count=review_count,
        pass_threshold=REVIEW_PASS_THRESHOLD,
        max_attempts=MAX_REVIEW_ATTEMPTS,
        next_node=destination,
        revision_target=destination,
    )
    return destination


def critique_for_culture(state: AggregatorState) -> str | None:
    target = state.get("revision_target")
    if target in ("culture_analysis", "both_analyses"):
        feedback = state.get("critique_feedback")
        return feedback if feedback else None
    return None


def critique_for_market(state: AggregatorState) -> str | None:
    target = state.get("revision_target")
    if target in ("market_analysis", "both_analyses"):
        feedback = state.get("critique_feedback")
        return feedback if feedback else None
    return None


def critique_for_master_report(state: AggregatorState) -> str | None:
    if state.get("revision_target") == "generate_report":
        feedback = state.get("critique_feedback")
        return feedback if feedback else None
    return None
