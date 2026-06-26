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

    # 조율 중인 이상향 (13축이 설계 원본, 8축은 파생)
    working_values: NotRequired[dict[str, float]]
    working_ideal: NotRequired[dict[str, float]]
    ideal_type: NotRequired[str]
    ideal_reasoning: NotRequired[str]

    # 산출
    final_response: NotRequired[str]
    current_step: NotRequired[str]
    error: NotRequired[str]
