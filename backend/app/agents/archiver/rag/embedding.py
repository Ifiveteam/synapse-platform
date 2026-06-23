"""Archiver RAG — 임베딩 생성 및 검색 쿼리 확장."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)


def embed_text_safe(text: str) -> list[float] | None:
    """OpenAI 임베딩을 생성한다. API 키 없음·실패 시 None."""
    normalized = text.strip()
    if not normalized or not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from app.agents.shared.embedding import embed_texts

        return embed_texts([normalized])[0]
    except Exception:
        logger.exception("Archiver RAG embedding failed")
        return None


def build_embedding_source(*, content: str, context_title: str | None = None) -> str:
    """저장·검색용 임베딩 입력 문자열을 조립한다."""
    body = content.strip()
    title = (context_title or "").strip()
    if title and title not in body:
        return f"[{title}]\n{body}"
    return body


def expand_rag_query(query_text: str, *, retrieval_attempt: int) -> str:
    """역주행 시도에 따라 RAG 검색 쿼리를 확장한다."""
    base = query_text.strip()
    if retrieval_attempt <= 1 or not base:
        return base

    # 2차+: 키워드 토큰을 공백으로 이어 넓은 의미 검색 유도
    tokens = re.findall(r"[\w가-힣]+", base)
    if len(tokens) >= 2:
        return " ".join(tokens)
    return base
