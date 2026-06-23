"""Critique 라우팅 trace."""

from __future__ import annotations

from app.agents.aggregator.trace._common import logger


def log_route_decision(
    *,
    score: int,
    review_count: int,
    pass_threshold: int,
    max_attempts: int,
    next_node: str,
    revision_target: str | None = None,
) -> None:
    reason: str
    if score >= pass_threshold:
        reason = f"검수 점수 {score}점 ≥ 합격 기준 {pass_threshold}점"
    elif review_count >= max_attempts:
        reason = f"최대 재시도 {max_attempts}회 도달 (현재 {review_count}회)"
    else:
        reason = (
            f"검수 점수 {score}점 < {pass_threshold}점 → "
            f"revision_target={revision_target or 'generate_report'} 역주행"
        )

    logger.info("  ┌─ 🔀 조건부 분기 (verify_report 이후)")
    logger.info("  │ 검수 점수 : %s점", score)
    logger.info("  │ 검수 횟수 : %s회", review_count)
    logger.info("  │ 재실행 대상: %s", revision_target or "(없음)")
    logger.info("  │ 분기 사유 : %s", reason)
    logger.info("  │ 다음 노드 : %s", next_node)
    logger.info("  └─ 라우팅 결정 완료")
