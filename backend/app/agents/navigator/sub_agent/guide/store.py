"""가이드 서브에이전트 RAG Port — catalog 검색을 repository에 위임."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from langchain_core.runnables import RunnableConfig

from app.agents.navigator.sub_agent._shared import (
    build_run_config as _build_run_config,
)
from app.agents.navigator.sub_agent._shared import (
    get_store as _get_store,
)
from app.agents.navigator.sub_agent.guide.schemas import CatalogHit


@runtime_checkable
class CatalogStore(Protocol):
    """catalog 의미 검색 Port (repository가 구현, service가 주입)."""

    async def search_by_axis(
        self,
        user_id: uuid.UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[CatalogHit]: ...


_GUIDE_STORE_KEY = "guide_catalog_store"


def build_run_config(store: CatalogStore | None) -> RunnableConfig:
    return _build_run_config(_GUIDE_STORE_KEY, store)


def get_store(config: RunnableConfig | None) -> CatalogStore | None:
    return _get_store(_GUIDE_STORE_KEY, config)
