"""Archiver 영속성 Port — Graph·Service와 DB Repository 경계."""

from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from app.agents.archiver.core.constants import ARCHIVER_STORE_KEY, RAG_SEARCH_LIMIT


class PastKnowledgeHit(BaseModel):
    """과거 기억 검색 1건 — Repository ↔ rag_node 계약."""

    role: str
    content: str
    context_title: str = Field(default="이전 웹페이지")
    created_at: str = Field(description="YYYY-MM-DD 형식")


@runtime_checkable
class ArchiverStore(Protocol):
    """Graph가 RAG 수집에 사용하는 최소 Store 계약."""

    async def search_past_knowledge(
        self,
        user_id: uuid.UUID,
        query_text: str,
        *,
        exclude_query_text: str | None = None,
        limit: int = RAG_SEARCH_LIMIT,
        retrieval_attempt: int = 1,
    ) -> list[PastKnowledgeHit]: ...


def build_run_config(*, store: ArchiverStore | None = None) -> dict[str, Any]:
    """LangGraph RunnableConfig — typed store 주입."""
    configurable: dict[str, Any] = {}
    if store is not None:
        configurable[ARCHIVER_STORE_KEY] = store
    return {"configurable": configurable}


def get_archiver_store(config: RunnableConfig) -> ArchiverStore | None:
    """RunnableConfig에서 ArchiverStore를 추출한다."""
    store = config.get("configurable", {}).get(ARCHIVER_STORE_KEY)
    if store is None:
        return None
    if not callable(getattr(store, "search_past_knowledge", None)):
        return None
    return store  # type: ignore[return-value]
