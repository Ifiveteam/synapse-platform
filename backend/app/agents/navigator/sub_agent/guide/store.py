"""가이드 서브에이전트 RAG Port — catalog 검색을 repository에 위임."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel


class CatalogHit(BaseModel):
    """축별 RAG로 찾은 실제 시청 영상 근거."""

    title: str
    channel: str
    category_id: str | None = None
    similarity: float = 0.0


@runtime_checkable
class CatalogStore(Protocol):
    """catalog 의미 검색 Port (repository가 구현, service가 주입)."""

    async def search_by_axis(
        self,
        user_id: uuid.UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[CatalogHit]: ...


GUIDE_STORE_KEY = "guide_catalog_store"


def build_run_config(store: CatalogStore | None) -> RunnableConfig:
    return {"configurable": {GUIDE_STORE_KEY: store}}


def get_store(config: RunnableConfig | None) -> CatalogStore | None:
    if not config:
        return None
    return config.get("configurable", {}).get(GUIDE_STORE_KEY)
