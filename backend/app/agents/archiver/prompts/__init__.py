"""Archiver agent prompt modules."""

from app.agents.archiver.prompts.builders import (
    build_basic_route_instruction,
    build_general_route_instruction,
    build_rag_route_instruction,
    build_search_collect_instruction,
    build_search_route_instruction,
)
from app.agents.archiver.prompts.router_prompt import build_router_prompt
from app.agents.archiver.prompts.system_prompt import (
    ARCHIVER_COMPREHENSIVE_TEMPLATE,
    ARCHIVER_GENERAL_TEMPLATE,
    ARCHIVER_RAG_TEMPLATE,
    ARCHIVER_SEARCH_COLLECT_TEMPLATE,
    ARCHIVER_SEARCH_RESPOND_TEMPLATE,
)
from app.agents.archiver.models import (
    NO_CONTEXT_BODY,
    NO_CONTEXT_TITLE,
    NO_CONTEXT_URL,
    NO_RAG_CONTEXT,
    OFF_TAB_BODY,
)

__all__ = [
    "ARCHIVER_COMPREHENSIVE_TEMPLATE",
    "ARCHIVER_GENERAL_TEMPLATE",
    "ARCHIVER_RAG_TEMPLATE",
    "ARCHIVER_SEARCH_COLLECT_TEMPLATE",
    "ARCHIVER_SEARCH_RESPOND_TEMPLATE",
    "NO_CONTEXT_BODY",
    "NO_CONTEXT_TITLE",
    "NO_CONTEXT_URL",
    "NO_RAG_CONTEXT",
    "OFF_TAB_BODY",
    "build_basic_route_instruction",
    "build_general_route_instruction",
    "build_rag_route_instruction",
    "build_router_prompt",
    "build_search_collect_instruction",
    "build_search_route_instruction",
]
