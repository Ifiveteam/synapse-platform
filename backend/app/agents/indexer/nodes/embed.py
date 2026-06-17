"""노드: catalog embedding_text 조합 + OpenAI 임베딩."""

from __future__ import annotations

import asyncio
import os

from app.agents.indexer.state import IndexerState
from app.agents.indexer.tool import build_catalog_embedding_text


async def node_embed(state: IndexerState) -> IndexerState:
    """제목·카테고리·태그·설명(300자) → embedding_text + vector."""
    try:
        items = state.get("cleaned_data") or []
        if not items:
            return {**state, "cleaned_data": [], "error": None}

        texts = [build_catalog_embedding_text(item) for item in items]
        enriched: list[dict] = [
            {**item, "embedding_text": text}
            for item, text in zip(items, texts, strict=False)
        ]

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(f"[embed] OPENAI_API_KEY 없음 — embedding_text만 ({len(items)}건)")
            return {**state, "cleaned_data": enriched, "error": None}

        from app.agents.shared.embedding import embed_texts

        print(f"[embed] OpenAI 임베딩 ({len(texts)}건)")
        vectors = await asyncio.get_event_loop().run_in_executor(
            None, embed_texts, texts
        )
        for item, vector in zip(enriched, vectors, strict=False):
            item["embedding"] = vector

        print(f"[embed] 완료 {len(vectors)}건")
        return {**state, "cleaned_data": enriched, "error": None}
    except Exception as e:
        return {**state, "error": str(e)}
