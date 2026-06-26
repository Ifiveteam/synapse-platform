"""Archiver 과거 기억 검색 전략 — keyword/vector 하이브리드 orchestration."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Protocol

from app.agents.archiver.core.constants import RAG_SEARCH_LIMIT
from app.agents.archiver.past_knowledge.embedding import expand_rag_query
from app.agents.archiver.core.store import PastKnowledgeHit
from app.models.chat import AIChatLog

logger = logging.getLogger(__name__)

_MAX_RAG_KEYWORDS = 5
_MIN_KEYWORD_LEN = 2
_RAG_CONTENT_PREVIEW_CHARS = 400


class PastKnowledgeSearchBackend(Protocol):
    """Repository가 제공하는 RAG SQL 실행 계약."""

    async def search_logs_by_keywords(
        self,
        *,
        user_id: uuid.UUID,
        query_text: str,
        limit: int,
        exclude_query_text: str | None,
        relaxed: bool,
    ) -> list[AIChatLog]: ...

    async def search_logs_by_vector(
        self,
        *,
        user_id: uuid.UUID,
        query_text: str,
        limit: int,
        exclude_query_text: str | None,
    ) -> list[AIChatLog]: ...


def extract_search_keywords(query_text: str) -> list[str]:
    """질문에서 검색용 키워드를 추출한다. (한글·영문 토큰 지원)"""
    tokens = re.findall(r"[\w가-힣]+", query_text)
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        normalized = token.strip().lower()
        if len(normalized) < _MIN_KEYWORD_LEN or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(normalized)
        if len(keywords) >= _MAX_RAG_KEYWORDS:
            break
    return keywords


def _truncate_content(content: str, limit: int = _RAG_CONTENT_PREVIEW_CHARS) -> str:
    text = content.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def logs_to_hits(logs: list[AIChatLog]) -> list[PastKnowledgeHit]:
    return [
        PastKnowledgeHit(
            role=log.role,
            content=_truncate_content(log.content),
            context_title=log.context_title or "이전 웹페이지",
            created_at=log.created_at.strftime("%Y-%m-%d"),
        )
        for log in logs
    ]


async def search_past_knowledge(
    backend: PastKnowledgeSearchBackend,
    user_id: uuid.UUID,
    query_text: str,
    limit: int = RAG_SEARCH_LIMIT,
    *,
    exclude_query_text: str | None = None,
    retrieval_attempt: int = 1,
) -> list[PastKnowledgeHit]:
    """과거 아카이버 대화를 키워드·벡터 하이브리드로 검색한다."""
    expanded_query = expand_rag_query(
        query_text,
        retrieval_attempt=retrieval_attempt,
    )

    logs: list[AIChatLog] = []
    if retrieval_attempt <= 1:
        logs = await backend.search_logs_by_keywords(
            user_id=user_id,
            query_text=expanded_query,
            limit=limit,
            exclude_query_text=exclude_query_text,
            relaxed=False,
        )
    else:
        logs = await backend.search_logs_by_vector(
            user_id=user_id,
            query_text=expanded_query,
            limit=limit,
            exclude_query_text=exclude_query_text,
        )
        if not logs:
            logger.info(
                "Archiver vector RAG miss — falling back to relaxed keyword search"
            )
            logs = await backend.search_logs_by_keywords(
                user_id=user_id,
                query_text=expanded_query,
                limit=limit,
                exclude_query_text=exclude_query_text,
                relaxed=True,
            )

    return logs_to_hits(logs)
