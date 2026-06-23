"""Archiver 워크플로우 진입·종료 trace."""

from __future__ import annotations

import textwrap
from typing import Any

from app.agents.archiver.trace.observability import log_event, log_workflow_summary
from app.agents.archiver.trace._common import banner, logger, truncate
from app.agents.archiver.models import ArchiverState, Evaluation, resolve_route


def log_workflow_start(*, state: ArchiverState) -> None:
    user_id = state.get("user_id", "?")
    session_id = state.get("session_id", "?")
    context_title = state.get("context_title", "(없음)")
    context_url = state.get("context_url", "(없음)")
    log_event(
        "workflow.start",
        session_id=session_id,
        user_id=user_id,
        context_title=context_title,
        context_url=context_url,
    )
    banner(
        f"🚀 Archiver 자율 루프 워크플로우 시작 | user={user_id} | session={session_id[:8]}…"
    )
    logger.info("  ┌─ 요청 컨텍스트")
    logger.info("  │ context_title : %s", context_title)
    logger.info("  │ context_url   : %s", context_url)
    logger.info("  └─ LangGraph State 초기화 완료")


def log_workflow_end(state: dict[str, Any], *, latency_ms: int) -> None:
    route_value = resolve_route(state).value  # type: ignore[arg-type]
    evaluation = Evaluation.from_state(state)  # type: ignore[arg-type]
    final_response = state.get("final_response") or ""
    error = state.get("error")
    session_id = state.get("session_id", "?")
    rag_hit = bool((state.get("rag_data") or "").strip())
    search_loops = int(state.get("search_attempts", 0))

    log_workflow_summary(
        session_id=session_id,
        route=route_value,
        eval_score=int(evaluation.is_sufficient) if evaluation else None,
        rag_hit=rag_hit,
        search_loops=search_loops,
        latency_ms=latency_ms,
        error=error,
    )
    banner(
        f"✅ Archiver 워크플로우 종료 | route={route_value} "
        f"| sufficient={evaluation.is_sufficient if evaluation else '—'} "
        f"| search_loops={search_loops} "
        f"| rag_hit={rag_hit} "
        f"| latency_ms={latency_ms}"
    )
    logger.info("  ┌─ 최종 스냅샷")
    logger.info("  │ 충분성        : %s", evaluation.is_sufficient if evaluation else "—")
    logger.info("  │ 권장 액션     : %s", evaluation.recommended_action if evaluation else "—")
    logger.info("  │ rag_data      : %s자", len(state.get("rag_data") or ""))
    logger.info("  │ search_data   : %s자", len(state.get("search_data") or ""))
    logger.info("  │ context_body  : %s자", len(state.get("context_body") or ""))
    logger.info("  │ final_response: %s자", len(final_response))
    if error:
        logger.info("  │ error         : %s", error)
    if final_response:
        preview = truncate(final_response, limit=120)
        logger.info("  │ 답변 미리보기 : %s", preview)
    logger.info("  └─ 워크플로우 trace 종료")


def log_node_enter(node: str, *, state: ArchiverState | None = None) -> None:
    route_label = resolve_route(state).value if state and state.get("route") else None
    log_event(
        "node.enter",
        node=node,
        route=route_label,
        session_id=state.get("session_id") if state else None,
        search_loops=state.get("search_attempts") if state else None,
    )
    logger.info("▶ [%s] 노드 진입", node)
    if not state:
        return

    route_label = resolve_route(state).value if state.get("route") else "(미분류)"

    if node == "router":
        logger.info("  └─ 유저 질문 라우팅 시작")

    elif node == "collect":
        logger.info("  └─ route=%s | retrieval_attempts=%s", route_label, state.get("retrieval_attempts", 0))

    elif node == "search":
        logger.info("  └─ route=%s | search_attempts=%s", route_label, state.get("search_attempts", 0))

    elif node == "evaluator":
        logger.info(
            "  └─ route=%s | rag=%s자 | search=%s자 | body=%s자",
            route_label,
            len(state.get("rag_data") or ""),
            len(state.get("search_data") or ""),
            len(state.get("context_body") or ""),
        )

    elif node == "respond":
        evaluation = Evaluation.from_state(state)
        logger.info(
            "  └─ route=%s | sufficient=%s",
            route_label,
            evaluation.is_sufficient if evaluation else "—",
        )
        if evaluation and evaluation.reason:
            for line in textwrap.wrap(evaluation.reason, width=68):
                logger.info("       %s", line)
