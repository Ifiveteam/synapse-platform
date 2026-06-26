"""Archiver 과거 기억 검색 — 임베딩 생성 및 DB 하이브리드 검색 전략.

LangGraph `nodes/rag.py`의 `rag_node`와 구분:
- 이 패키지: DB 영속화·임베딩·키워드/벡터 검색 (Repository/Store 레이어)
- `nodes/rag.py` (`rag_node`): 그래프 런타임 노드 — Store Port만 호출
"""
