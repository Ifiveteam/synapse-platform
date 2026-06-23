"""Archiver LangGraph State — 수집 엔진별 격리 필드 및 fan-in 헬퍼."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ── 수집 엔진 노드명 (확장 시 이 집합에 추가) ─────────────────────

COLLECT_NODE = "collect_node"
RAG_NODE = "rag_node"
SEARCH_NODE = "search_node"

ALL_COLLECT_ENGINES: frozenset[str] = frozenset(
    {COLLECT_NODE, RAG_NODE, SEARCH_NODE},
)


def merge_executed_steps(left: list[str] | None, right: list[str] | None) -> list[str]:
    """병렬 트랙이 각자 기록한 executed_steps를 순서 보존 합집합으로 병합한다."""
    merged: list[str] = list(left or [])
    seen = set(merged)
    for step in right or []:
        if step not in seen:
            merged.append(step)
            seen.add(step)
    return merged


class ArchiverState(TypedDict):
    """LangGraph 실행 상태 — 엔진별 수집 결과를 격리 저장한다."""

    messages: Annotated[list[BaseMessage], add_messages]

    user_id: uuid.UUID
    session_id: NotRequired[str]
    context_title: str
    context_url: str

    route: NotRequired[str]
    is_general: NotRequired[bool]
    target_engines: NotRequired[list[str]]
    executed_steps: Annotated[NotRequired[list[str]], merge_executed_steps]

    # 엔진별 격리 수집 필드
    context_dom: NotRequired[str]
    context_rag: NotRequired[str]
    context_search: NotRequired[str]

    # 하위 호환 (클라이언트 주입·레거시 노드)
    context_body: NotRequired[str]
    dom_continuation: NotRequired[bool]
    rag_data: NotRequired[str]
    search_data: NotRequired[str]

    evaluation_result: NotRequired[dict[str, Any]]
    retrieval_attempts: NotRequired[int]
    search_attempts: NotRequired[int]

    final_response: NotRequired[str]
    system_instruction: NotRequired[str]

    current_step: NotRequired[str]
    error: NotRequired[str]


def get_context_dom(state: ArchiverState) -> str:
    """DOM/페이지 본문 — context_dom 우선, 레거시 context_body 폴백."""
    return (state.get("context_dom") or state.get("context_body") or "").strip()


def get_context_rag(state: ArchiverState) -> str:
    """내부 RAG — context_rag 우선, 레거시 rag_data 폴백."""
    return (state.get("context_rag") or state.get("rag_data") or "").strip()


def get_context_search(state: ArchiverState) -> str:
    """웹 검색 — context_search 우선, 레거시 search_data 폴백."""
    return (state.get("context_search") or state.get("search_data") or "").strip()


def normalize_target_engines(raw: list[str] | None) -> list[str]:
    """알 수 없는 노드명을 제거하고 ALL_COLLECT_ENGINES 순서로 정렬한다."""
    if not raw:
        return []
    allowed_order = [COLLECT_NODE, RAG_NODE, SEARCH_NODE]
    seen: set[str] = set()
    ordered: list[str] = []
    for name in allowed_order:
        if name in raw and name not in seen:
            ordered.append(name)
            seen.add(name)
    return ordered


def remaining_engines(state: ArchiverState) -> list[str]:
    """이번 세션에서 아직 실행되지 않은 전체 수집 엔진 목록."""
    executed = set(state.get("executed_steps") or [])
    return [e for e in normalize_target_engines(list(ALL_COLLECT_ENGINES)) if e not in executed]
