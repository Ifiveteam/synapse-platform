"""OpenAI embedding helper (text-embedding-3-small, 1536)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

EMBEDDING_MODEL = "text-embedding-3-small"
_BATCH = 100

_openai_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """OpenAI 클라이언트 지연 생성 — import 시점엔 키를 요구하지 않는다."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트를 배치로 임베딩. 입력 순서를 유지해 반환."""
    if not texts:
        return []

    client = _get_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH):
        chunk = texts[start : start + _BATCH]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=chunk,
        )
        vectors.extend(item.embedding for item in response.data)
    return vectors
