"""OpenAI embedding helper (text-embedding-3-small, 1536)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
_BATCH = 100


def embed_texts(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트를 배치로 임베딩. 입력 순서를 유지해 반환."""
    if not texts:
        return []

    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH):
        chunk = texts[start : start + _BATCH]
        response = _openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=chunk,
        )
        vectors.extend(item.embedding for item in response.data)
    return vectors
