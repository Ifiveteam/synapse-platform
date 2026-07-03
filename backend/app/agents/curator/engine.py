"""Curator LangGraph 워크플로우 — 툴 기반 에이전트.

agent_node가 툴 선택과 최종 답변 생성을 모두 담당한다 (별도 respond 노드 없음).
respond 노드로 분리했을 때, agent_node가 만든 답변을 버리고 respond가 컨텍스트를
따로(부정확하게) 재구성해 다시 생성하면서 에코·날짜 환각·무관정보 재활용 버그가
반복됐다 — 원인은 이중 생성 자체와 수동 컨텍스트 재구성이었다.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.constants import (
    GEMINI_API_KEY_ENV_VARS,
    GEMINI_MODEL,
    RECENT_CONTEXT_WINDOW,
    STREAM_ERROR_MESSAGE,
)
from app.agents.curator.tools import build_tools
from app.agents.curator.types import CuratorState, CuratorStreamEvent

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))

_SYSTEM_PROMPT_BASE = """
당신은 Synapse 플랫폼의 AI 큐레이터입니다.
유저의 YouTube 시청 데이터를 분석하고, 재생목록 생성·스크랩 저장 등의 작업을 실제로 수행할 수 있습니다.

## 플랫폼 경로 (페이지 안내 시 사용)
- 이상향 목록: /me/ideals
- 이상향 설계: /me/ideals/setup
- 재생목록: /me/playlists
- 스크랩: /me/scraps
- 성향 분석: /me/analyses
- 테이크아웃 업로드: /upload

페이지 경로를 안내할 때는 마크다운 링크로 버튼을 만드세요. 예: [이상향 보러가기](/me/ideals)

## 툴 호출 규칙 (필수)
- 재생목록 요청("재생목록 만들어줘", "플레이리스트 만들어줘", "영상 목록 만들어줘") → create_playlist 즉시 호출.
- URL 저장 요청("저장해줘", "북마크해줘", "스크랩해줘" + URL) → save_scrap 즉시 호출.
- 유저 데이터 질문("내 성향", "많이 본 영상", "구독 채널" 등) → query_db 등 조회 툴 호출.
- 일반 지식 질문은 툴 없이 바로 답변하세요.
- "지원하지 않습니다", "제공되지 않습니다", "직접 만들어 드릴 수 없습니다"라고 말하지 마세요.
- 툴이 있는데 거절하지 마세요. 이미 조회된 데이터가 있으면 "업로드하세요"로 회피하지 말고 그 데이터로 답하세요.

## 답변 원칙 (툴 호출 없이 바로 답할 때)
- 지금 답해야 할 건 유저의 가장 마지막 메시지 하나뿐입니다. 그 메시지에만 정확히 답하세요.
- <최근_대화>는 "그거", "그 중에", "거기서" 같은 지시어를 해석할 때만 참고하세요.
  지금 질문이 이전과 다른 주제면 그 안의 내용을 답변에 절대 가져오지 마세요.
  예: 직전에 시청 기록 얘기를 했는데 지금 구독 채널을 물었다면, 시청 기록 얘기는 다시 꺼내지 말고
  구독 채널 질문에만 답하세요.
- "안녕하세요", "저는 Synapse 큐레이터입니다" 같은 자기소개로 시작하지 마세요. 바로 본론으로 답하세요.
- 인사나 짧은 말에는 자연스럽게 짧게 답하세요.
- 마크다운을 적극 활용하세요 (볼드, 목록, 인용 등).
- 핵심만 간결하게 전달하고, 불필요한 서론·결론은 생략하세요.
- 유저를 판단하거나 평가하지 마세요.
- <유저_데이터>가 있으면 그 데이터만 근거로 답하세요. 데이터에 없는 내용은 절대 지어내지 마세요.
- <유저_데이터>가 없는 일반 질문(음식, 날씨, 추천 등)은 일반 지식으로 자유롭게 답변하세요.
""".strip()


def _current_date_kst() -> str:
    """한국 시간 기준 오늘 날짜. 안 넣으면 Gemini가 날짜를 지어내 대화마다 다른 '오늘'을 답한다."""
    now = datetime.now(_KST)
    return f"{now.year}년 {now.month}월 {now.day}일"


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "")
            for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        )
    return str(content) if content else ""


def _truncate_at_boundary(text: str, limit: int = 60) -> str:
    """문장 중간에 끊긴 것처럼 보이지 않도록 완결된 경계에서 자릅니다."""
    if len(text) <= limit:
        return text
    window = text[:limit]
    boundary = max((window.rfind(p) for p in ".!?:\n"), default=-1)
    if boundary != -1:
        return window[: boundary + 1].strip()
    idx = window.rfind(" ")
    if idx != -1:
        return window[:idx].strip() + "."
    return window.strip() + "."


def _extract_tool_context(messages: list[BaseMessage]) -> str:
    """이번 턴에 실행된 ToolMessage 내용을 수집합니다."""
    parts = [m.content for m in messages if isinstance(m, ToolMessage) and m.content]
    return "\n\n".join(str(p) for p in parts) if parts else ""


def _build_recent_context(messages: list[BaseMessage], window: int) -> str:
    """이전 대화(현재 턴 이전)를 실제 turn이 아닌 참고 텍스트로 요약합니다.
    과거 답변을 실제 대화 turn으로 섞으면 Gemini가 그 turn을 이어서 마무리해야 한다고
    착각해 에코가 발생하므로, system prompt 안 참고 자료로만 전달한다.
    """
    last_human_idx = -1
    for i, m in enumerate(messages):
        if isinstance(m, HumanMessage):
            last_human_idx = i
    if last_human_idx <= 0:
        return ""

    lines: list[str] = []
    for m in messages[:last_human_idx]:
        if isinstance(m, HumanMessage):
            lines.append(f"유저: {_message_text(m.content).strip()}")
        elif (
            isinstance(m, AIMessage)
            and not getattr(m, "tool_calls", None)
            and m.content
        ):
            text = _message_text(m.content).strip()
            if text:
                lines.append(f"AI: {_truncate_at_boundary(text, 60)}")
    return "\n".join(lines[-window * 2 :])


def _build_turn_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """이번 턴에 실제로 오간 메시지만 반환합니다 (마지막 HumanMessage부터).
    과거 턴은 _build_recent_context로 system prompt에만 전달하고, 여기엔 이번 턴의
    유저 메시지 + (툴 호출 루프 중이면) AIMessage(tool_calls)/ToolMessage만 남긴다.
    """
    last_human_idx = -1
    for i, m in enumerate(messages):
        if isinstance(m, HumanMessage):
            last_human_idx = i
    if last_human_idx == -1:
        return []
    return list(messages[last_human_idx:])


def _build_system_prompt(state: CuratorState) -> str:
    messages = state.get("messages", [])
    instruction = f"{_SYSTEM_PROMPT_BASE}\n\n[오늘 날짜] {_current_date_kst()}"

    recent_context = _build_recent_context(messages, RECENT_CONTEXT_WINDOW)
    if recent_context:
        instruction += f"""

---
<최근_대화>
{recent_context}
</최근_대화>"""

    tool_context = _extract_tool_context(messages)
    if tool_context:
        instruction += f"""

---
아래는 이번 턴에 조회한 유저의 실제 데이터입니다. 이 데이터만 근거로 답변하세요.
데이터에 없는 내용은 절대 지어내지 마세요.

<유저_데이터>
{tool_context}
</유저_데이터>"""

    return instruction


def _get_api_key() -> str:
    for env_var in GEMINI_API_KEY_ENV_VARS:
        key = os.getenv(env_var)
        if key:
            return key
    raise ValueError("Gemini API 키가 없습니다.")


def _route_agent(state: CuratorState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


_ACTION_TOOLS = {"create_playlist", "save_scrap"}

_ACTION_TOOL_TRIGGERS: dict[str, list[str]] = {
    "create_playlist": ["재생목록", "플레이리스트", "playlist"],
    "save_scrap": ["저장해", "북마크해", "스크랩해", "save this", "bookmark"],
}


def _detect_forced_tool(state: CuratorState) -> str | None:
    """마지막 사용자 메시지에서 액션 키워드를 감지해 강제 툴 이름을 반환합니다."""
    has_tool_results = any(isinstance(m, ToolMessage) for m in state["messages"])
    if has_tool_results:
        return None

    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    if not last_human:
        return None

    text = str(last_human.content).lower()
    for tool_name, keywords in _ACTION_TOOL_TRIGGERS.items():
        if any(kw in text for kw in keywords):
            return tool_name
    return None


def build_graph(db: AsyncSession, user_id: uuid.UUID):
    tools = build_tools(db, user_id)
    tools_by_name = {t.name: t for t in tools}

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=_get_api_key(),
        temperature=0.6,
    )
    llm_with_tools = llm.bind_tools(tools)

    async def agent_node(state: CuratorState) -> dict[str, Any]:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        writer({"event": "status", "content": "🤔 분석 중..."})

        system_prompt = _build_system_prompt(state)
        turn_messages = _build_turn_messages(state.get("messages", []))
        messages = [SystemMessage(content=system_prompt), *turn_messages]

        forced = _detect_forced_tool(state)
        if forced and forced in tools_by_name:
            invoke_llm = llm.bind_tools(tools, tool_choice=forced)
        else:
            invoke_llm = llm_with_tools

        full = None
        try:
            async for chunk in invoke_llm.astream(messages):
                full = chunk if full is None else full + chunk
                if not getattr(chunk, "tool_call_chunks", None):
                    text = _message_text(chunk.content)
                    if text:
                        writer({"event": "token", "content": text})
        except Exception:
            logger.exception("Curator agent_node streaming failed")
            writer({"event": "token", "content": STREAM_ERROR_MESSAGE})
            return {"messages": [AIMessage(content=STREAM_ERROR_MESSAGE)]}

        tool_calls = getattr(full, "tool_calls", None) or []
        text = _message_text(full.content if full is not None else "").strip()

        if not tool_calls and not text:
            fallback = "죄송해요, 답변을 생성하지 못했습니다. 다시 질문해 주세요."
            writer({"event": "token", "content": fallback})
            return {"messages": [AIMessage(content=fallback)]}

        return {"messages": [AIMessage(content=full.content, tool_calls=tool_calls)]}

    def _route_after_tools(state: CuratorState) -> str:
        last = state["messages"][-1]
        if isinstance(last, ToolMessage) and last.name in _ACTION_TOOLS:
            return "relay"
        return "agent"

    async def relay_node(state: CuratorState) -> dict[str, Any]:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        last_tool = next(
            (m for m in reversed(state["messages"]) if isinstance(m, ToolMessage)),
            None,
        )
        if last_tool and last_tool.content:
            writer({"event": "token", "content": str(last_tool.content)})
        return {}

    graph = StateGraph(CuratorState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("relay", relay_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        _route_agent,
        {"tools": "tools", "end": END},
    )
    graph.add_conditional_edges(
        "tools",
        _route_after_tools,
        {"relay": "relay", "agent": "agent"},
    )
    graph.add_edge("relay", END)

    return graph.compile()


class CuratorEngine:
    @staticmethod
    def build_initial_state(
        *,
        messages: list[BaseMessage],
        user_id: uuid.UUID,
        session_id: str,
    ) -> CuratorState:
        return {
            "messages": messages,
            "user_id": user_id,
            "session_id": session_id,
        }

    async def stream(
        self,
        *,
        initial_state: CuratorState,
        db: AsyncSession,
    ) -> AsyncIterator[CuratorStreamEvent]:
        user_id = initial_state["user_id"]
        graph = build_graph(db, user_id)

        async for mode, chunk in graph.astream(
            initial_state,
            stream_mode=["custom", "values"],
        ):
            if mode != "custom" or not isinstance(chunk, dict):
                continue

            event_type = chunk.get("event")
            content = chunk.get("content")
            if not content or event_type not in {"status", "token", "chart"}:
                continue

            yield CuratorStreamEvent(event=event_type, content=content)


_engine: CuratorEngine | None = None


def get_curator_engine() -> CuratorEngine:
    global _engine
    if _engine is None:
        _engine = CuratorEngine()
    return _engine
