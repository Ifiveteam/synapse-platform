"""스크랩 임베딩 영속화 레포지토리."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrap_embedding import ScrapEmbedding


class ScrapEmbeddingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_embedding(
        self,
        *,
        scrap_id: uuid.UUID,
        embedding_text: str,
        embedding: list[float],
    ) -> ScrapEmbedding:
        """스크랩 1건에 대한 임베딩을 저장한다."""
        row = ScrapEmbedding(
            scrap_id=scrap_id,
            embedding_text=embedding_text,
            embedding=embedding,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row
