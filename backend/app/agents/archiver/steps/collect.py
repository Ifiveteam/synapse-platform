"""collect 스텝 — RAG 검색 및 BASIC 경로 페이지 본문 수집."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.types import RunnableConfig

from app.agents.archiver.steps._common import latest_user_message
from app.agents.archiver.steps.rag import format_past_knowledge_for_rag
from app.agents.archiver.steps.scraper import is_scrapable_url, scrape_context_body
from app.agents.archiver.store import get_archiver_store
from app.agents.archiver.trace import log_collect_result, log_node_enter
from app.agents.archiver.types import (
    MAX_RETRIEVAL_ATTEMPTS,
    NO_CONTEXT_BODY,
    OFF_TAB_BODY,
    ArchiverRoute,
    ArchiverState,
    resolve_route,
)

logger = logging.getLogger(__name__)


async def collect(
    state: ArchiverState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """RAG·BASIC 경로에 따라 내부 지식 또는 활성 탭 본문을 수집한다."""
    log_node_enter("collect", state=state)
    route = resolve_route(state)
    writer = get_stream_writer()
    patch: dict[str, Any] = {"current_step": "collect"}
    rag_payload = state.get("rag_data") or ""
    context_body = state.get("context_body") or ""
    retrieval_attempts = state.get("retrieval_attempts", 0)

    if route == ArchiverRoute.RAG:
        retrieval_attempts += 1
        patch["retrieval_attempts"] = retrieval_attempts

        if retrieval_attempts > MAX_RETRIEVAL_ATTEMPTS:
            logger.warning("Archiver RAG retrieval max attempts reached")
            log_collect_result(
                route=route.value,
                rag_chars=len(rag_payload),
                context_body_chars=len(context_body),
                retrieval_attempts=retrieval_attempts,
                rag_hit=bool(rag_payload.strip()),
            )
            return patch

        writer(
            {
                "event": "status",
                "content": (
                    "🧠 [Internal RAG] 과거 보관함 기억을 검색합니다"
                    + (
                        f" (시도 {retrieval_attempts} — 의미 기반 재검색)...\n\n"
                        if retrieval_attempts > 1
                        else "...\n\n"
                    )
                ),
            }
        )

        store = get_archiver_store(config)
        user_message = latest_user_message(state)
        rag_payload = ""

        if store is not None:
            hits = await store.search_past_knowledge(
                user_id=state["user_id"],
                query_text=user_message,
                exclude_query_text=user_message,
                retrieval_attempt=retrieval_attempts,
            )
            rag_payload = format_past_knowledge_for_rag(hits)

        patch["rag_data"] = rag_payload
        log_collect_result(
            route=route.value,
            rag_chars=len(rag_payload),
            context_body_chars=len(context_body),
            retrieval_attempts=retrieval_attempts,
            rag_hit=bool(rag_payload.strip()),
        )
        return patch

    if route == ArchiverRoute.BASIC:
        writer(
            {
                "event": "status",
                "content": "🌐 [Context] 현재 페이지 본문을 분석 중입니다...\n\n",
            }
        )

        context_body = OFF_TAB_BODY
        context_url = state.get("context_url", "")

        if is_scrapable_url(context_url):
            scraped = (
                await scrape_context_body(
                    context_title=state.get("context_title", ""),
                    context_url=context_url,
                )
            ).strip()
            if scraped and scraped not in {NO_CONTEXT_BODY, OFF_TAB_BODY}:
                context_body = scraped

        patch["context_body"] = context_body
        log_collect_result(
            route=route.value,
            rag_chars=len(rag_payload),
            context_body_chars=len(context_body),
            retrieval_attempts=retrieval_attempts,
            rag_hit=False,
        )
        return patch

    logger.warning("Archiver collect step invoked for unsupported route: %s", route.value)
    return patch
