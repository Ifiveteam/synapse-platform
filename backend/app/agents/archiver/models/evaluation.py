"""Archiver evaluator — LLM Structured Output + LangGraph state 겸용."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.archiver.core.constants import MAX_SEARCH_ATTEMPTS

from .state import (
    COLLECT_NODE,
    RAG_NODE,
    SEARCH_NODE,
    ArchiverState,
    get_context_dom,
    get_context_rag,
    get_context_search,
    remaining_engines,
)

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
        for key in ("dom_verdict", "rag_verdict", "search_verdict"):
            data.setdefault(key, "not_run")
        return cls.model_validate(data)

    @classmethod
    def fallback(cls, *, state: ArchiverState) -> Evaluation:
        """LLM evaluator 실패 시 보수적 소스 진단 + 남은 엔진 재시도."""
        search_attempts = state.get("search_attempts", 0)
        pending = remaining_engines(state)
        dom = get_context_dom(state)
        rag = get_context_rag(state)
        search = get_context_search(state)
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

        if search_attempts < MAX_SEARCH_ATTEMPTS and SEARCH_NODE in pending:
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
