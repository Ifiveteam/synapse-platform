"""Archiver RAG 도메인 — 임베딩 생성 및 하이브리드 검색 전략.

LangGraph `nodes/rag.py`의 `rag_node`와 구분:
- 이 패키지: DB 영속화·임베딩·키워드/벡터 검색 (Repository/Store 레이어)
- `nodes/rag.py`: 그래프 런타임 노드 — Store Port만 호출
"""

from app.agents.archiver.rag.embedding import (
    build_embedding_source,
    embed_text_safe,
    expand_rag_query,
)
from app.agents.archiver.rag.retrieval import (
    PastKnowledgeSearchBackend,
    extract_search_keywords,
    search_past_knowledge,
)

__all__ = [
    "PastKnowledgeSearchBackend",
    "build_embedding_source",
    "embed_text_safe",
    "expand_rag_query",
    "extract_search_keywords",
    "search_past_knowledge",
]
