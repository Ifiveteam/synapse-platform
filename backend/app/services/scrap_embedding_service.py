"""스크랩 본문 임베딩 생성·영속화."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db
from app.repositories.scrap_embedding_repository import ScrapEmbeddingRepository

logger = logging.getLogger(__name__)


def build_scrap_embedding_text(
    *,
    title: str | None,
    summary: str,
    raw_body: str | None,
) -> str:
    """임베딩 입력 문자열을 조립한다. 본문 우선, 제목은 맥락으로 접두."""
    body = (raw_body or summary).strip()
    normalized_title = (title or "").strip()
    if normalized_title and normalized_title not in body:
        return f"[{normalized_title}]\n{body}"
    return body


async def embed_text_async(text: str) -> list[float] | None:
    """OpenAI text-embedding-3-small(1536) 임베딩. 키 없음·실패 시 None."""
    normalized = text.strip()
    if not normalized:
        return None

    try:
        from app.agents.shared.embedding import embed_texts

        vectors = await asyncio.to_thread(embed_texts, [normalized])
        return vectors[0] if vectors else None
    except Exception:
        logger.exception("Scrap embedding failed")
        return None


class ScrapEmbeddingService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.repo = ScrapEmbeddingRepository(db)

    async def embed_and_persist(
        self,
        *,
        scrap_id: uuid.UUID,
        title: str | None,
        summary: str,
        raw_body: str | None,
    ) -> None:
        """스크랩 본문을 임베딩하여 scrap_embeddings에 저장한다."""
        embedding_text = build_scrap_embedding_text(
            title=title,
            summary=summary,
            raw_body=raw_body,
        )
        vector = await embed_text_async(embedding_text)
        if vector is None:
            logger.warning(
                "Scrap %s embedding skipped (no API key or empty text)",
                scrap_id,
            )
            return

        await self.repo.upsert_embedding(
            scrap_id=scrap_id,
            embedding_text=embedding_text,
            embedding=vector,
        )
