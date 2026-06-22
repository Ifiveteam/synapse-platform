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
유저 질문을 분석해서 라우트를 결정하세요.

MY_DATA  — 유저 본인 데이터가 필요한 질문
           (내 취향, 내 시청기록, 내 성향, 내 프로필, 내가 본 영상 등)

GENERAL  — 일반 지식으로 답할 수 있는 질문
           (유튜브 트렌드, 채널 추천, 알고리즘, 콘텐츠 팁 등)

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
    else:
        route = CuratorRoute.GENERAL

    writer({"event": "status", "content": f"🔀 [{route.value}] 경로로 처리합니다..."})

    return {"route": route}
