"""Navigator LangGraph 실행 상태 (대화형 이상향 설계 루프)."""

from __future__ import annotations

import uuid
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class NavigatorState(TypedDict):
    """챗봇 이상향 설계 그래프의 실행 상태 가방."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: uuid.UUID
    session_id: NotRequired[str]

    # 분석 입력 (근거)
    profile_21: dict[str, float]
    current_8axis: dict[str, float]
    top_interests: NotRequired[dict[str, list]]
    portrait: NotRequired[dict]  # 성향·도메인 초상 (인터뷰 주 근거)

    # 조율 중인 이상향 (13축이 설계 원본, 8축은 파생 / 성향·도메인이 표시 축)
    working_values: NotRequired[dict[str, float]]
    working_ideal: NotRequired[dict[str, float]]
    working_disposition: NotRequired[dict[str, float]]
    working_interest: NotRequired[dict[str, float]]
    working_keywords: NotRequired[list[str]]  # 대화에서 뽑은 구체 관심 키워드
    ideal_type: NotRequired[str]
    ideal_reasoning: NotRequired[str]
    persona_label: NotRequired[str]

    # 인터뷰 루프 제어
    turn: NotRequired[int]  # 이번 턴 번호(사용자 발화 수)
    force_finalize: NotRequired[bool]  # 확정 버튼
    taste_notes: NotRequired[str]  # 누적 취향 이해
    missing: NotRequired[list[str]]  # 더 물어보면 좋을 측면
    sufficient: NotRequired[
        bool
    ]  # AI가 이상향 만들 만큼 충분하다고 판단(마무리 안내용)
    decision: NotRequired[str]  # "ask" | "finalize"

    # 산출
    final_response: NotRequired[str]
    current_step: NotRequired[str]
    error: NotRequired[str]
