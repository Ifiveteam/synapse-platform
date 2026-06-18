"""워크플로우 진입·종료 trace."""

from __future__ import annotations

import textwrap
from typing import Any

from app.agents.aggregator.trace._common import banner, logger


def log_workflow_start() -> None:
    banner("🚀 Aggregator 멀티 에이전트 워크플로우 시작")


def log_assemble_workflow_start() -> None:
    banner("⚡ Aggregator 데이터 조립 전용 워크플로우 시작 (Gemini 미호출)")


def log_assemble_workflow_end(state: dict[str, Any]) -> None:
    integrated = state.get("integrated_data") or {}
    profile = integrated.get("internal_user_stats", {}).get("cognitive_bias_map", {})
    banner(
        f"✅ 데이터 조립 완료 | 코호트={profile.get('cohort_size', '?')}명 "
        f"| 8각 축={len(profile.get('axes', []))}개"
    )


def log_workflow_end(state: dict[str, Any]) -> None:
    score = state.get("verification_score")
    review_count = state.get("review_count", 0)
    report_json = state.get("report_json") or {}
    headline = (
        report_json.get("headline_summary", "") if isinstance(report_json, dict) else ""
    )
    banner(
        f"✅ 워크플로우 종료 | 검수 점수={score}점 | 검수 횟수={review_count}회 "
        f"| headline={headline[:60] or '(없음)'}"
    )


def log_node_enter(node: str, *, state: dict[str, Any] | None = None) -> None:
    logger.info("▶ [%s] 노드 진입", node)
    if not state:
        return

    if node == "generate_report":
        attempt = state.get("review_count", 0) + 1
        logger.info("  └─ 리포트 생성 시도 #%s", attempt)
        feedback = state.get("critique_feedback")
        if feedback:
            logger.info("  └─ 이전 검수 피드백 반영:")
            for line in textwrap.wrap(feedback, width=68):
                logger.info("       %s", line)

    if node == "verify_report":
        logger.info("  └─ 현재 누적 검수 횟수: %s회", state.get("review_count", 0))
