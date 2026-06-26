"""Archiver 경로별 시스템 프롬프트 빌더 (자율형 라우팅 최적화 버전)."""

from __future__ import annotations

from app.agents.archiver.models import (
    NO_CONTEXT_BODY,
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    NO_RAG_CONTEXT,
)
from app.agents.archiver.prompts.context import format_archiver_current_date
from app.agents.archiver.prompts.system_prompt import (
    ARCHIVER_COMPREHENSIVE_TEMPLATE,
    ARCHIVER_GENERAL_TEMPLATE,
    ARCHIVER_RAG_TEMPLATE,
    ARCHIVER_SEARCH_COLLECT_TEMPLATE,
    ARCHIVER_SEARCH_RESPOND_TEMPLATE,
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
        current_date=format_archiver_current_date(),
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


def build_search_collect_instruction(
    *,
    context_title: str | None = None,
    context_url: str | None = None,
) -> str:
    """search_node 수집 단계 — Google Search Tool 호출용 지시."""
    return ARCHIVER_SEARCH_COLLECT_TEMPLATE.format(
        current_date=format_archiver_current_date(),
        context_title=context_title or NO_CONTEXT_TITLE,
        context_url=context_url or NO_CONTEXT_URL,
    )


def build_search_route_instruction(
    *,
    context_title: str | None = None,
    context_url: str | None = None,
) -> str:
    """SEARCH respond 경로 — 수집된 검색 결과 기반 답변 프롬프트."""
    return ARCHIVER_SEARCH_RESPOND_TEMPLATE.format(
        current_date=format_archiver_current_date(),
        context_title=context_title or NO_CONTEXT_TITLE,
        context_url=context_url or NO_CONTEXT_URL,
    )


def build_general_route_instruction() -> str:
    """GENERAL 경로 — 일상 대화 및 스몰토크 전용 프롬프트 빌더."""
    return ARCHIVER_GENERAL_TEMPLATE


def build_synthesis_route_instruction(
    *,
    context_title: str | None = None,
    context_url: str | None = None,
    context_dom: str | None = None,
    context_rag: str | None = None,
    context_search: str | None = None,
) -> str:
    """채워진 근거(dom·rag·search)를 종합하는 respond synthesis 프롬프트."""
    sections: list[str] = [
        "당신은 Synapse Archiver 에이전트입니다. 아래 **여러 채널**에서 수집한 정보를 종합해 한국어로 답하세요.",
        f"[오늘 날짜] {format_archiver_current_date()}",
        (
            "[활성 탭] "
            f"{context_title or NO_CONTEXT_TITLE} / {context_url or NO_CONTEXT_URL}"
        ),
    ]

    dom = (context_dom or "").strip()
    if dom:
        sections.append(f"[현재 페이지 본문]\n{dom}")

    rag = (context_rag or "").strip()
    if rag:
        sections.append(f"[과거 기억·스크랩 (RAG)]\n{rag}")

    search = (context_search or "").strip()
    if search:
        sections.append(
            f"[웹 검색 결과]\n{search}\n\n외부 사실은 이 섹션만 근거로 사용하세요."
        )

    if not any((dom, rag, search)):
        sections.append("(수집된 근거 없음 — 대화 맥락만으로 답하세요)")

    sections.append(
        "⚠️ [답변 규칙]\n"
        "1. 각 섹션에 있는 사실만 근거로 사용하고 교차 검증해 종합하세요.\n"
        "2. 없는 정보는 추측하지 마세요.\n"
        "3. 수집 과정·도구는 언급하지 마세요."
    )
    return "\n\n".join(sections)
