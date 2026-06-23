"""Archiver 구조화 JSON observability — 운영 로그 수집기 파싱용 한 줄 이벤트."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("app.agents.archiver.observability")


def log_event(event: str, /, **fields: Any) -> None:
    """단일 JSON 라인으로 archiver 이벤트를 기록한다."""
    payload: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "agent": "archiver",
        "event": event,
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    logger.info("%s", json.dumps(payload, ensure_ascii=False, default=str))


def log_workflow_summary(
    *,
    session_id: str,
    route: str,
    eval_score: int | None,
    rag_hit: bool,
    search_loops: int,
    latency_ms: int,
    error: str | None = None,
) -> None:
    """요청 1건 요약 — route/score/loop/latency를 한 줄로 파악한다."""
    log_event(
        "workflow.end",
        session_id=session_id,
        route=route,
        eval_score=eval_score,
        rag_hit=rag_hit,
        search_loops=search_loops,
        latency_ms=latency_ms,
        error=error,
    )
