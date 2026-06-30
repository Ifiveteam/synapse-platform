"""Archiver agent prompt modules."""

from app.agents.archiver.prompts.builders import (
    build_basic_route_instruction,
    build_general_route_instruction,
    build_rag_route_instruction,
    build_scrap_followup_summary_instruction,
    build_search_collect_instruction,
    build_search_route_instruction,
    build_synthesis_route_instruction,
)
from app.agents.archiver.prompts.router_prompt import build_router_prompt

__all__ = [
    "build_basic_route_instruction",
    "build_general_route_instruction",
    "build_rag_route_instruction",
    "build_router_prompt",
    "build_scrap_followup_summary_instruction",
    "build_search_collect_instruction",
    "build_search_route_instruction",
    "build_synthesis_route_instruction",
]
