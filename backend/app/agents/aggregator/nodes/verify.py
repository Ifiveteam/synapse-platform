"""verify_report 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.nodes._helpers import NODE_VERIFY, require_integrated_data
from app.agents.aggregator.report import coerce_dashboard_report
from app.agents.aggregator.routing import build_verification_state_patch
from app.agents.aggregator.state import (
    MAX_REVIEW_ATTEMPTS,
    REVIEW_PASS_THRESHOLD,
    AggregatorState,
)
from app.agents.aggregator.sub_agent import run_report_verification
from app.agents.aggregator.trace import (
    log_node_enter,
    log_verification_result,
    logger,
)


async def verify_report_node(state: AggregatorState) -> dict[str, Any]:
    """시니어 검수자: Structured Output으로 채점 후 상태를 결정론적으로 갱신한다."""
    log_node_enter(NODE_VERIFY, state=state)
    integrated_data = require_integrated_data(state)

    raw_report = state.get("report_json")
    if not raw_report:
        msg = "report_json이 상태에 없습니다. generate_report 노드 이후에 실행하세요."
        raise ValueError(msg)

    report = coerce_dashboard_report(raw_report)
    logger.info("  ┌─ 검수 대상 리포트: headline=%s", report.headline_summary[:80])
    logger.info("  └─ Gemini 시니어 검수자(Structured Output) 호출 중…")

    result = await run_report_verification(report, integrated_data)
    review_count = state.get("review_count", 0) + 1
    state_patch = build_verification_state_patch(result, review_count=review_count)

    log_verification_result(
        score=state_patch["verification_score"],
        feedback=state_patch["critique_feedback"],
        is_template_valid=state_patch["is_template_valid"],
        revision_target=state_patch["revision_target"],
        review_count=state_patch["review_count"],
        pass_threshold=REVIEW_PASS_THRESHOLD,
        max_attempts=MAX_REVIEW_ATTEMPTS,
    )

    return {**state_patch, "error": None}
