"""Archiver 도메인 타입 — Route, Evaluation, StreamEvent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.archiver.core.constants import MAX_RETRIEVAL_ATTEMPTS, MAX_SEARCH_ATTEMPTS
from app.agents.archiver.models.state import (
    ALL_COLLECT_ENGINES,
    COLLECT_NODE,
    RAG_NODE,
    SEARCH_NODE,
    ArchiverState,
    get_context_dom,
    get_context_rag,
    get_context_search,
    merge_executed_steps,
    normalize_target_engines,
    remaining_engines,
)

__all__ = [
    "ALL_COLLECT_ENGINES",
    "COLLECT_NODE",
    "MAX_RETRIEVAL_ATTEMPTS",
    "MAX_SEARCH_ATTEMPTS",
    "NO_CONTEXT_BODY",
    "NO_CONTEXT_TITLE",
    "NO_CONTEXT_URL",
    "NO_RAG_CONTEXT",
    "OFF_TAB_BODY",
    "RAG_NODE",
    "SEARCH_NODE",
    "ArchiverRoute",
    "ArchiverState",
    "ArchiverStreamEvent",
    "CollectEngineName",
    "Evaluation",
    "EvaluatorAction",
    "RouterTargets",
    "StreamEventType",
    "derive_route_from_targets",
    "get_context_dom",
    "get_context_rag",
    "get_context_search",
    "merge_executed_steps",
    "normalize_target_engines",
    "parse_archiver_route",
    "remaining_engines",
    "resolve_route",
]

# ── Context placeholders (프롬프트·State 초기값 SSOT) ─────────────

NO_CONTEXT_TITLE = "알 수 없음 (시스템 도메인 또는 빈 화면)"
NO_CONTEXT_URL = "N/A"
NO_CONTEXT_BODY = "(본문을 수집하지 못했습니다. 제목·URL 맥락만 사용하세요.)"
NO_RAG_CONTEXT = "(현재 세션에 연결된 내부 지식 가방이 없습니다.)"
OFF_TAB_BODY = "사용자가 웹페이지 외부(빈 화면 등)에서 대화 중입니다."

# ── Route ──────────────────────────────────────────────────────────

_VALID_ROUTES = frozenset({"BASIC", "RAG", "SEARCH", "GENERAL"})


class ArchiverRoute(StrEnum):
    BASIC = "BASIC"
    RAG = "RAG"
    SEARCH = "SEARCH"
    GENERAL = "GENERAL"


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


def derive_route_from_targets(
    targets: list[str],
    *,
    is_general: bool = False,
) -> ArchiverRoute:
    """다중 엔진 타겟에서 respond 온도·프롬프트용 대표 route를 도출한다."""
    normalized = normalize_target_engines(targets)
    if is_general and not normalized:
        return ArchiverRoute.GENERAL
    if len(normalized) == 1:
        sole = normalized[0]
        if sole == COLLECT_NODE:
            return ArchiverRoute.BASIC
        if sole == RAG_NODE:
            return ArchiverRoute.RAG
        if sole == SEARCH_NODE:
            return ArchiverRoute.SEARCH
    if COLLECT_NODE in normalized and SEARCH_NODE not in normalized and RAG_NODE not in normalized:
        return ArchiverRoute.BASIC
    if RAG_NODE in normalized and SEARCH_NODE not in normalized:
        return ArchiverRoute.RAG
    if SEARCH_NODE in normalized:
        return ArchiverRoute.SEARCH
    if COLLECT_NODE in normalized:
        return ArchiverRoute.BASIC
    return ArchiverRoute.GENERAL


def parse_archiver_route(raw: str) -> ArchiverRoute:
    """모델 출력에서 라우트 키워드를 추출한다. 실패 시 GENERAL로 폴백."""
    token = raw.strip().upper()
    if token in _VALID_ROUTES:
        return ArchiverRoute(token)

    # GENERAL은 다른 route 키워드보다 나중에 매칭 (과잉 GENERAL 방지)
    priority = (
        ArchiverRoute.SEARCH,
        ArchiverRoute.RAG,
        ArchiverRoute.BASIC,
        ArchiverRoute.GENERAL,
    )
    for route in priority:
        if route.value in token:
            return route

    return ArchiverRoute.GENERAL


# ── Stream ────────────────────────────────────────────────────────

StreamEventType = Literal["status", "token", "need_dom"]


def resolve_route(state: ArchiverState) -> ArchiverRoute:
    """State에서 ArchiverRoute를 안전하게 추출한다."""
    route = state.get("route")
    if isinstance(route, ArchiverRoute):
        return route
    if isinstance(route, str):
        return parse_archiver_route(route)
    return ArchiverRoute.GENERAL


# ── Evaluation (LLM Structured Output + LangGraph state 겸용) ─────

SourceVerdict = Literal["sufficient", "insufficient", "irrelevant", "empty", "not_run"]
EvaluatorAction = Literal["search", "rag", "collect", "none"]


class Evaluation(BaseModel):
    """evaluator 채점 결과 — 다중 엔진 병렬 수집 통합 심사."""

    is_sufficient: bool = Field(
        description=(
            "dom·rag·search 소스를 종합했을 때 유저 질문에 신뢰할 수 있게 "
            "답변 가능하면 True. 하나라도 필수 소스가 부족하면 False."
        ),
    )
    reason: str = Field(
        description=(
            "종합 판정 근거. 각 소스(dom/rag/search)의 상태와 "
            "질문 의도 대비 부족한 점을 한국어 2~4문장으로 명확히 기술."
        ),
    )
    recommended_action: EvaluatorAction = Field(
        description=(
            "불충분 시 pending_engines 중 다음에 켤 엔진: "
            "search=외부 검색, rag=과거 기억, collect=DOM 재수집, "
            "none=추가 수집 없이 답변. 충분하면 반드시 none."
        ),
    )
    dom_verdict: SourceVerdict = Field(
        description="context_dom(현장 데이터) 소스별 심사 결과",
    )
    rag_verdict: SourceVerdict = Field(
        description="context_rag(과거 기억) 소스별 심사 결과",
    )
    search_verdict: SourceVerdict = Field(
        description="context_search(외부 검색) 소스별 심사 결과",
    )

    def to_state_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: ArchiverState) -> Evaluation | None:
        raw = state.get("evaluation_result")
        if not raw:
            return None
        data = dict(raw)
        # 레거시 recommended_action 마이그레이션
        legacy_action = data.get("recommended_action")
        if legacy_action == "respond":
            data["recommended_action"] = "none"
        elif legacy_action == "collect" and "dom_verdict" not in data:
            data["recommended_action"] = "rag"
        for key in ("dom_verdict", "rag_verdict", "search_verdict"):
            data.setdefault(key, "not_run")
        return cls.model_validate(data)

    def normalized_action(self) -> EvaluatorAction:
        """레거시 action 값을 현재 스키마로 정규화한다."""
        action = self.recommended_action
        if action == "respond":  # type: ignore[comparison-overlap]
            return "none"
        return action

    @classmethod
    def fallback(cls, *, state: ArchiverState) -> Evaluation:
        """LLM evaluator 실패 시 보수적 소스 진단 + 남은 엔진 재시도."""
        from app.agents.archiver.models.state import (
            COLLECT_NODE,
            RAG_NODE,
            SEARCH_NODE,
            remaining_engines,
        )

        search_attempts = state.get("search_attempts", 0)
        pending = remaining_engines(state)
        dom = (state.get("context_dom") or state.get("context_body") or "").strip()
        rag = (state.get("context_rag") or state.get("rag_data") or "").strip()
        search = (state.get("context_search") or state.get("search_data") or "").strip()
        executed = set(state.get("executed_steps") or [])

        def _verdict(collected: str, node: str) -> SourceVerdict:
            if node not in executed:
                return "not_run"
            if not collected:
                return "empty"
            return "insufficient"

        dom_v = _verdict(dom, COLLECT_NODE)
        rag_v = _verdict(rag, RAG_NODE)
        search_v = _verdict(search, SEARCH_NODE)

        if (
            search_attempts < MAX_SEARCH_ATTEMPTS
            and SEARCH_NODE in pending
        ):
            return cls(
                is_sufficient=False,
                reason="LLM evaluator 실패 — 외부 검색(search_node) 재시도가 필요합니다.",
                recommended_action="search",
                dom_verdict=dom_v,
                rag_verdict=rag_v,
                search_verdict=search_v,
            )

        if RAG_NODE in pending and search_attempts >= MAX_SEARCH_ATTEMPTS:
            return cls(
                is_sufficient=False,
                reason="LLM evaluator 실패 — 과거 기억(rag_node) 보강을 시도합니다.",
                recommended_action="rag",
                dom_verdict=dom_v,
                rag_verdict=rag_v,
                search_verdict=search_v,
            )

        if COLLECT_NODE in pending:
            return cls(
                is_sufficient=False,
                reason="LLM evaluator 실패 — 현장 DOM(collect_node) 수집을 시도합니다.",
                recommended_action="collect",
                dom_verdict=dom_v,
                rag_verdict=rag_v,
                search_verdict=search_v,
            )

        return cls(
            is_sufficient=False,
            reason="LLM evaluator 실패 — 추가 수집 불가, best-effort 답변으로 진행합니다.",
            recommended_action="none",
            dom_verdict=dom_v,
            rag_verdict=rag_v,
            search_verdict=search_v,
        )


@dataclass(frozen=True, slots=True)
class ArchiverStreamEvent:
    """SSE 스트림 이벤트 — status(UI 안내)와 token(답변 본문)을 구분한다."""

    event: StreamEventType
    content: str
