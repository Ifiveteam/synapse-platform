"""가이드 서브에이전트 상수 — 루프 한도 · RAG 검색용 축 설명."""

from __future__ import annotations

MAX_RETRIEVE_ATTEMPTS = 2
MAX_GEN_ATTEMPTS = 2
WEAK_AXES_TOP_K = 3
CATALOG_SEARCH_LIMIT = 5

# RAG 검색 쿼리용 8축 설명 (키/라벨만으론 임베딩 검색이 약해서 문장으로)
AXIS_QUERY_TEXT: dict[str, str] = {
    "exploration": "새로운 주제와 낯선 분야를 폭넓게 탐색하는 콘텐츠",
    "analytical": "비판적이고 논리적인 분석, 심층 리뷰와 해설 콘텐츠",
    "creativity": "창작 과정, 만들기, 예술과 독창적 아이디어 콘텐츠",
    "execution": "실천 튜토리얼, 따라 하기, 문제 해결 How-to 콘텐츠",
    "achievement_drive": "목표 달성, 자기계발, 생산성과 성장 콘텐츠",
    "autonomy": "스스로 결정하고 주도적으로 학습하는 자기주도 콘텐츠",
    "sociality": "사람·관계·커뮤니티, 사회적 상호작용 콘텐츠",
    "sensitivity": "감성·정서·공감, 위로와 감정 표현 콘텐츠",
}


def axis_query(axis: str, relax_level: int) -> str:
    """완화 레벨이 오르면 쿼리를 더 일반적으로 넓힌다 (재검색용)."""
    base = AXIS_QUERY_TEXT.get(axis, axis)
    if relax_level <= 0:
        return base
    return f"{base}. {axis} 성향과 조금이라도 관련된 다양한 영상"
