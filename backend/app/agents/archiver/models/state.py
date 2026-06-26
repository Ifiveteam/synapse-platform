"""Archiver LangGraph State — 수집 엔진별 격리 필드 및 fan-in 헬퍼."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
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

    # @deprecated 레거시 — 신규 코드는 is_general + target_engines 사용
    route: NotRequired[str]
    is_general: NotRequired[bool]
    target_engines: NotRequired[list[str]]
    executed_steps: Annotated[NotRequired[list[str]], merge_executed_steps]

    # 엔진별 격리 수집 필드 (canonical)
    context_dom: NotRequired[str]
    context_rag: NotRequired[str]
    context_search: NotRequired[str]

    dom_continuation: NotRequired[bool]

    evaluation_result: NotRequired[dict[str, Any]]
    retrieval_attempts: NotRequired[int]
    search_attempts: NotRequired[int]

    final_response: NotRequired[str]
    system_instruction: NotRequired[str]

    current_step: NotRequired[str]
    error: NotRequired[str]


# 레거시 State 키 (TypedDict 미포함, 쓰기 금지): context_body, rag_data, search_data
# → get_context_dom / get_context_rag / get_context_search 가 읽기 전용 폴백 제공


def latest_user_message(state: ArchiverState) -> str:
    """messages 스택에서 마지막 HumanMessage 본문을 추출한다."""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
    return ""


_ROUTER_DIALOGUE_SNIPPET_MAX_CHARS = 500


def recent_dialogue_snippet(
    state: ArchiverState,
    *,
    max_chars: int = _ROUTER_DIALOGUE_SNIPPET_MAX_CHARS,
) -> str:
    """라우터용 직전 대화 요약 — 현재 user 턴은 제외한다."""
    messages: list[BaseMessage] = list(state.get("messages") or [])
    if messages and isinstance(messages[-1], HumanMessage):
        messages = messages[:-1]
    if not messages:
        return "(없음)"

    lines: list[str] = []
    for message in messages[-4:]:
        if isinstance(message, HumanMessage):
            role = "사용자"
        elif isinstance(message, AIMessage):
            role = "어시스턴트"
        else:
            continue
        content = message.content
        text = content.strip() if isinstance(content, str) else str(content).strip()
        if text:
            lines.append(f"{role}: {text}")

    snippet = "\n".join(lines)
    if not snippet:
        return "(없음)"
    if len(snippet) > max_chars:
        return snippet[: max_chars - 3] + "..."
    return snippet


def has_prior_dialogue(state: ArchiverState) -> bool:
    """현재 user 턴을 제외한 직전 대화가 있는지 (멀티턴 세션)."""
    messages = list(state.get("messages") or [])
    return len(messages) > 1 and recent_dialogue_snippet(state) != "(없음)"


def format_turn_with_dialogue(state: ArchiverState, current_text: str) -> str:
    """수집·검색 쿼리용 — 직전 대화 블록 + 현재 질문."""
    stripped = current_text.strip()
    if not stripped:
        return stripped
    snippet = recent_dialogue_snippet(state)
    if snippet == "(없음)":
        return stripped
    return f"[직전 대화]\n{snippet}\n\n[현재 질문]\n{stripped}"


def enrich_collect_query(state: ArchiverState, query: str) -> str:
    """멀티턴이면 search/RAG 쿼리에 직전 대화를 붙인다."""
    base = query.strip()
    if not base or not has_prior_dialogue(state):
        return base
    return format_turn_with_dialogue(state, base)


def get_context_dom(state: ArchiverState) -> str:
    """DOM/페이지 본문 — context_dom 우선, 레거시 context_body 폴백."""
    return (state.get("context_dom") or state.get("context_body") or "").strip()


def get_context_rag(state: ArchiverState) -> str:
    """과거 기억 — context_rag 우선, 레거시 rag_data 폴백."""
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
