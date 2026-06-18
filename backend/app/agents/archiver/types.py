"""Archiver 내부 도메인 타입 — Route, State, Evaluation, StreamEvent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.agents.archiver.constants import MAX_RETRIEVAL_ATTEMPTS, MAX_SEARCH_ATTEMPTS

__all__ = [
    "MAX_RETRIEVAL_ATTEMPTS",
    "MAX_SEARCH_ATTEMPTS",
    "NO_CONTEXT_BODY",
    "NO_CONTEXT_TITLE",
    "NO_CONTEXT_URL",
    "NO_RAG_CONTEXT",
    "OFF_TAB_BODY",
    "ArchiverRoute",
    "ArchiverState",
    "ArchiverStep",
    "ArchiverStreamEvent",
    "Evaluation",
    "EvaluationResult",
    "EvaluatorAction",
    "LlmEvaluationOutput",
    "StreamEventType",
    "parse_archiver_route",
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


def parse_archiver_route(raw: str) -> ArchiverRoute:
    """모델 출력에서 라우트 키워드를 추출한다. 실패 시 GENERAL로 폴백."""
    token = raw.strip().upper()
    if token in _VALID_ROUTES:
        return ArchiverRoute(token)

    for route in ArchiverRoute:
        if route.value in token:
            return route

    return ArchiverRoute.GENERAL


# ── LangGraph State ───────────────────────────────────────────────

ArchiverStep = Literal[
    "router",
    "collect",
    "search",
    "evaluator",
    "respond",
]

StreamEventType = Literal["status", "token"]


class ArchiverState(TypedDict):
    """LangGraph 실행 상태 — 수집·평가·생성 단계를 누적 추적한다."""

    messages: Annotated[list[BaseMessage], add_messages]

    user_id: int
    session_id: NotRequired[str]
    context_title: str
    context_url: str

    route: NotRequired[ArchiverRoute]
    context_body: NotRequired[str]
    rag_data: NotRequired[str]
    search_data: NotRequired[str]

    evaluation_result: NotRequired[dict[str, Any]]
    retrieval_attempts: NotRequired[int]
    search_attempts: NotRequired[int]

    final_response: NotRequired[str]
    system_instruction: NotRequired[str]

    current_step: NotRequired[str]
    error: NotRequired[str]


def resolve_route(state: ArchiverState) -> ArchiverRoute:
    """State에서 ArchiverRoute를 안전하게 추출한다."""
    route = state.get("route")
    if isinstance(route, ArchiverRoute):
        return route
    if isinstance(route, str):
        return parse_archiver_route(route)
    return ArchiverRoute.GENERAL


# ── Evaluation (LLM Structured Output + LangGraph state 겸용) ─────

EvaluatorAction = Literal["respond", "search", "collect"]


class Evaluation(BaseModel):
    """evaluator 채점 결과 — Gemini JSON과 state 저장 형식을 통합."""

    is_sufficient: bool = Field(
        description=(
            "수집된 rag_data·search_data·context_body만으로 "
            "유저 질문에 신뢰할 수 있게 답변 가능하면 True"
        ),
    )
    score: int = Field(
        ge=0,
        le=100,
        description="근거 충분성 점수 (0=전무, 100=완벽)",
    )
    reason: str = Field(
        description="판단 근거를 한국어 1~2문장으로 요약",
    )
    recommended_action: EvaluatorAction = Field(
        description=(
            "respond=답변 생성, search=외부 검색 역주행, "
            "collect=내부 지식 재검색"
        ),
    )

    def to_state_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: ArchiverState) -> Evaluation | None:
        raw = state.get("evaluation_result")
        if not raw:
            return None
        return cls.model_validate(raw)

    @classmethod
    def fallback(cls, *, state: ArchiverState) -> Evaluation:
        """LLM evaluator 실패 시 보수적 best-effort / search 재시도."""
        search_attempts = state.get("search_attempts", 0)
        route = resolve_route(state)

        if search_attempts < MAX_SEARCH_ATTEMPTS and route in {
            ArchiverRoute.RAG,
            ArchiverRoute.SEARCH,
            ArchiverRoute.BASIC,
        }:
            return cls(
                is_sufficient=False,
                score=25,
                reason="LLM evaluator 실패 — 웹 검색 재시도",
                recommended_action="search",
            )

        return cls(
            is_sufficient=True,
            score=40,
            reason="LLM evaluator 실패 — best-effort 생성",
            recommended_action="respond",
        )


# 하위 호환 alias
LlmEvaluationOutput = Evaluation
EvaluationResult = Evaluation


@dataclass(frozen=True, slots=True)
class ArchiverStreamEvent:
    """SSE 스트림 이벤트 — status(UI 안내)와 token(답변 본문)을 구분한다."""

    event: StreamEventType
    content: str
