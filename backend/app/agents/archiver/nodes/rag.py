"""rag_node — 사용자 과거 기억/맥락을 context_rag에 수집한다.

LangGraph 수집 엔진 노드. 런타임 검색은 `ArchiverStore.search_past_knowledge` Port에 위임한다.
임베딩·SQL 하이브리드 전략은 `app.agents.archiver.past_knowledge` 패키지에 있으며,
Repository/Store 구현체가 담당한다 (이 노드는 직접 import하지 않음).
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.types import RunnableConfig

from app.agents.archiver.core.constants import MAX_RETRIEVAL_ATTEMPTS
from app.agents.archiver.core.store import PastKnowledgeHit, get_archiver_store
from app.agents.archiver.models import (
    RAG_NODE,
    ArchiverState,
    enrich_collect_query,
    get_context_dom,
    get_context_rag,
    latest_user_message,
)
from app.agents.archiver.protocols.stream_status import (
    MSG_RAG_FIRST,
    MSG_RAG_RETRY,
    status_event,
)
from app.agents.archiver.trace import log_collect_result, log_node_enter

logger = logging.getLogger(__name__)


def format_past_knowledge_for_rag(hits: list[PastKnowledgeHit]) -> str:
    """PastKnowledgeHit 목록을 에이전트가 읽기 쉬운 과거 기억 파편 문자열로 변환한다."""
    if not hits:
        return ""

    return "\n".join(
        (
            f"[{item.created_at} 스크랩/대화 힌트 - '{item.context_title}']\n"
            f"- 발화자: {item.role}\n"
            f"- 내용: {item.content}\n"
        )
        for item in hits
    )


async def rag_node(
    state: ArchiverState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자 과거 기억/맥락을 context_rag에 수집한다."""
    log_node_enter("rag_node", state=state)
    writer = get_stream_writer()
    retrieval_attempts = state.get("retrieval_attempts", 0) + 1
    patch: dict[str, Any] = {
        "executed_steps": [RAG_NODE],
        "retrieval_attempts": retrieval_attempts,
    }

    if retrieval_attempts > MAX_RETRIEVAL_ATTEMPTS:
        logger.warning("Archiver RAG retrieval max attempts reached")
        prior = get_context_rag(state)
        if prior:
            patch["context_rag"] = prior
        return patch

    rag_status = MSG_RAG_RETRY if retrieval_attempts > 1 else MSG_RAG_FIRST
    writer(status_event(rag_status, phase="rag"))

    store = get_archiver_store(config)
    user_message = latest_user_message(state)
    rag_query = enrich_collect_query(state, user_message)
    rag_payload = ""

    if store is not None:
        hits = await store.search_past_knowledge(
            user_id=state["user_id"],
            query_text=rag_query,
            exclude_query_text=user_message,
            retrieval_attempt=retrieval_attempts,
        )
        rag_payload = format_past_knowledge_for_rag(hits)

    patch["context_rag"] = rag_payload
    log_collect_result(
        route="RAG",
        rag_chars=len(rag_payload),
        context_body_chars=len(get_context_dom(state)),
        retrieval_attempts=retrieval_attempts,
        rag_hit=bool(rag_payload.strip()),
    )
    return patch
