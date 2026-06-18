"""Archiver 경로별 시스템 프롬프트 빌더 (자율형 라우팅 최적화 버전)."""

from __future__ import annotations

from app.agents.archiver.prompts.system_prompt import (
    ARCHIVER_COMPREHENSIVE_TEMPLATE,
    ARCHIVER_GENERAL_TEMPLATE,
    ARCHIVER_RAG_TEMPLATE,
    ARCHIVER_SEARCH_TEMPLATE,
)
from app.agents.archiver.types import (
    NO_CONTEXT_BODY,
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    NO_RAG_CONTEXT,
)


def build_basic_route_instruction(
    *,
    context_title: str | None = None,
    context_url: str | None = None,
    context_body: str | None = None,
) -> str:
    """BASIC 경로 — 현재 활성 탭 본문 분석을 위한 프롬프트 빌더."""
    body = (context_body or "").strip()
    return ARCHIVER_COMPREHENSIVE_TEMPLATE.format(
        context_title=context_title or NO_CONTEXT_TITLE,
        context_url=context_url or NO_CONTEXT_URL,
        context_body=body if body else NO_CONTEXT_BODY,
    )


def build_rag_route_instruction(*, past_rag_knowledge: str | None = None) -> str:
    """RAG 경로 — 유저의 과거 기록 파편 기반 프롬프트 빌더."""
    rag_payload = (past_rag_knowledge or "").strip()
    rag_section = (
        f"[내부 지식 가방(RAG) - 유저의 과거 기록 파편]\n{rag_payload}"
        if rag_payload
        else NO_RAG_CONTEXT
    )
    return ARCHIVER_RAG_TEMPLATE.format(rag_context=rag_section)


def build_search_route_instruction(
    *,
    context_title: str | None = None,
    context_url: str | None = None,
) -> str:
    """SEARCH 경로 — 외부 구글 웹 검색 전용 프롬프트 빌더."""
    return ARCHIVER_SEARCH_TEMPLATE.format(
        context_title=context_title or NO_CONTEXT_TITLE,
        context_url=context_url or NO_CONTEXT_URL,
    )


def build_general_route_instruction() -> str:
    """GENERAL 경로 — 일상 대화 및 스몰토크 전용 프롬프트 빌더."""
    return ARCHIVER_GENERAL_TEMPLATE
