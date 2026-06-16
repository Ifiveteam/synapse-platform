"""retrieve_rag_context 노드 — 내부 지식 가방(RAG) 검색 (2단계 확장 포인트)."""

from __future__ import annotations

from typing import Any

from app.agents.archiver.prompt import NO_RAG_CONTEXT
from app.agents.archiver.state import ArchiverState


async def retrieve_rag_context_node(
    state: ArchiverState,
    user_message: str,
) -> dict[str, Any]:
    """유저 질문에 맞는 내부 지식을 검색한다. (현재는 스텁 — pgvector 연동 예정)"""
    _ = (state, user_message)
    return {"rag_context": NO_RAG_CONTEXT}
