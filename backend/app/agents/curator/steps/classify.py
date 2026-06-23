"""classify 노드 — 질문을 MY_DATA / GENERAL 로 분류한다."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from app.agents.curator.gemini import invoke_structured_safe
from app.agents.curator.types import (
    CuratorRoute,
    CuratorState,
    RouteDecision,
)

logger = logging.getLogger(__name__)

_ROUTER_PROMPT = """
유저 질문을 분석해서 route와 needed_sources를 결정하세요.

## route
MY_DATA  — 유저 본인 데이터가 필요한 질문 (내 취향, 내 시청기록, 내 성향 등)
GENERAL  — 일반 지식으로 답할 수 있는 질문 (트렌드, 알고리즘, 채널 추천 등)

## needed_sources (MY_DATA일 때만, 꼭 필요한 것만 선택)
- profile        : 성향·취향·페르소나·요약 관련 질문
- stats          : 총 시청 수, 카테고리 비율, 통계 관련 질문
- channels       : 자주 본 채널, 채널 목록 관련 질문
- recent         : 최근·요즘 시청한 영상 관련 질문 (쇼츠 제외)
- shorts         : 최근 본 쇼츠(Shorts) 영상 관련 질문
- vector_catalog : 특정 주제·키워드로 내 시청 영상 검색이 필요할 때
- vector_analysis: 영상의 내용·분석·요약이 필요할 때

GENERAL이면 needed_sources는 빈 배열로 하세요.

질문: {question}
"""


def _latest_user_message(state: CuratorState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    return ""


async def classify(state: CuratorState) -> dict[str, Any]:
    writer = get_stream_writer()
    question = _latest_user_message(state)

    decision = await invoke_structured_safe(
        system_instruction=_ROUTER_PROMPT.format(question=question),
        user_content=question,
        schema=RouteDecision,
        temperature=0.0,
    )

    if decision is not None:
        route = CuratorRoute(decision.route)
        needed_sources = decision.needed_sources if route == CuratorRoute.MY_DATA else []
    else:
        route = CuratorRoute.GENERAL
        needed_sources = []

    writer({"event": "status", "content": f"🔀 [{route.value}] 경로로 처리합니다..."})

    return {"route": route, "needed_sources": needed_sources}
