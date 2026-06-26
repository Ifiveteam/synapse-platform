"""Archiver models — LangGraph State + Pydantic 도메인 (Barrel / 단일 진입점).

하위 모듈(`state`, `routing`, `evaluation`, `stream_events`, `context`)은 독립 파일로 유지한다.
외부 코드는 반드시 `from app.agents.archiver.models import ...` 만 사용한다.
"""

from app.agents.archiver.core.constants import (
    MAX_RETRIEVAL_ATTEMPTS,
    MAX_SEARCH_ATTEMPTS,
)

from .context import (
    NO_CONTEXT_BODY,
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    NO_RAG_CONTEXT,
    OFF_TAB_BODY,
)
from .evaluation import Evaluation
from .routing import (
    RouterTargets,
    format_router_trace_label,
    wants_page_context,
)
from .state import (
    COLLECT_NODE,
    RAG_NODE,
    SEARCH_NODE,
    ArchiverState,
    enrich_collect_query,
    format_turn_with_dialogue,
    get_context_dom,
    get_context_rag,
    get_context_search,
    has_prior_dialogue,
    latest_user_message,
    normalize_target_engines,
    recent_dialogue_snippet,
    remaining_engines,
)
from .stream_events import ArchiverStreamEvent, StatusPhase, StreamEventType

__all__ = [
    # context
    "NO_CONTEXT_BODY",
    "NO_CONTEXT_TITLE",
    "NO_CONTEXT_URL",
    "NO_RAG_CONTEXT",
    "OFF_TAB_BODY",
    # state
    "COLLECT_NODE",
    "RAG_NODE",
    "SEARCH_NODE",
    "ArchiverState",
    "enrich_collect_query",
    "format_turn_with_dialogue",
    "get_context_dom",
    "get_context_rag",
    "get_context_search",
    "has_prior_dialogue",
    "latest_user_message",
    "normalize_target_engines",
    "recent_dialogue_snippet",
    "remaining_engines",
    # routing
    "RouterTargets",
    "format_router_trace_label",
    "wants_page_context",
    # evaluation
    "Evaluation",
    # stream_events
    "ArchiverStreamEvent",
    "StatusPhase",
    "StreamEventType",
    # constants (re-exported from core)
    "MAX_RETRIEVAL_ATTEMPTS",
    "MAX_SEARCH_ATTEMPTS",
]
