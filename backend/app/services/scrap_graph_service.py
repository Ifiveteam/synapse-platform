"""스크랩 하이브리드 그래프 페이로드 조립."""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.repositories.scrap_graph_repository import ScrapGraphRepository
from app.schemas.scrap_graph import ScrapGraphLink, ScrapGraphNode, ScrapGraphResponse


def _parse_csv_param(value: str | None) -> list[str] | None:
    """쉼표 구분 쿼리 파라미터를 정규화된 문자열 리스트로 변환한다."""
    if not value:
        return None
    items = [part.strip() for part in value.split(",") if part.strip()]
    return items or None


class ScrapGraphService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.repo = ScrapGraphRepository(db)

    async def get_graph(
        self,
        *,
        user_id: uuid.UUID,
        categories: str | None = None,
        tags: str | None = None,
    ) -> ScrapGraphResponse:
        """유저 스코프 스크랩 그래프 nodes + links를 반환한다."""
        category_list = _parse_csv_param(categories)
        tag_list = _parse_csv_param(tags)

        node_rows = await self.repo.fetch_graph_nodes(
            user_id=user_id,
            categories=category_list,
            tags=tag_list,
        )
        link_rows = await self.repo.fetch_graph_links(
            user_id=user_id,
            categories=category_list,
            tags=tag_list,
        )

        nodes = [ScrapGraphNode.model_validate(row) for row in node_rows]
        links = [ScrapGraphLink.model_validate(row) for row in link_rows]
        return ScrapGraphResponse(nodes=nodes, links=links)
