"""RAG 포맷터 — Store 검색 결과를 프롬프트 주입용 문자열로 변환."""

from __future__ import annotations

from app.agents.archiver.store import PastKnowledgeHit


def format_past_knowledge_for_rag(hits: list[PastKnowledgeHit]) -> str:
    """PastKnowledgeHit 목록을 에이전트가 읽기 쉬운 과거 기억 파편 문자열로 변환한다."""
    if not hits:
        return ""

    return "\n".join(
        (
            f"[{item.created_at} 스크랩/대화 힌트 - '{item.context_title}']\n"
            f"- 발화자: {item.role}\n"
            f"- 내용: {item.content}\n"
        )
        for item in hits
    )
