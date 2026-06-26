"""Archiver 라우팅 — RouterTargets, trace 라벨, DOM 필요 여부."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .state import (
    COLLECT_NODE,
    ArchiverState,
    normalize_target_engines,
)

CollectEngineName = Literal["collect_node", "rag_node", "search_node"]


class RouterTargets(BaseModel):
    """router LLM Structured Output — 1차 병렬 실행 대상 엔진 목록."""

    targets: list[CollectEngineName] = Field(
        default_factory=list,
        description=(
            "수집 엔진 목록. 일상 대화·인사면 반드시 빈 배열 []. "
            '예: [], ["search_node"], ["collect_node","search_node"]'
        ),
    )
    is_general: bool = Field(
        default=False,
        description=(
            "인사·감사·짧은 리액션만이면 true (이때 targets는 반드시 []). "
            '예: "안녕"→true, "ㅎㅇ"→true, "날씨 알려줘"→false'
        ),
    )


def format_router_trace_label(
    state: ArchiverState | None = None,
    *,
    is_general: bool = False,
    target_engines: list[str] | None = None,
) -> str:
    """trace·로그용 라우터 라벨 — SSOT: is_general + target_engines."""
    if state is not None:
        is_general = bool(state.get("is_general"))
        target_engines = state.get("target_engines")
    if is_general:
        return "general"
    targets = normalize_target_engines(target_engines)
    if not targets:
        return "general"
    return "+".join(targets)


def wants_page_context(state: ArchiverState) -> bool:
    """collect_node가 라우팅·실행 대상이면 페이지(DOM) 맥락이 필요한 경로."""
    targets = normalize_target_engines(state.get("target_engines"))
    executed = set(state.get("executed_steps") or [])
    return COLLECT_NODE in targets or COLLECT_NODE in executed
