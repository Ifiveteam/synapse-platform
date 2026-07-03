"""Navigator LangGraph 노드 공통 유틸."""

from __future__ import annotations

from google.genai import types
from langchain_core.messages import BaseMessage, HumanMessage

from app.agents.navigator.state import NavigatorState


def latest_user_message(state: NavigatorState) -> str:
    """messages 스택에서 마지막 HumanMessage 본문을 추출한다."""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            content = message.content
            return content.strip() if isinstance(content, str) else str(content).strip()
    return ""


def conversation_transcript(state: NavigatorState, limit: int = 12) -> str:
    """최근 대화를 '사용자/네비게이터' 라벨 트랜스크립트로 렌더 (취향 누적 근거)."""
    messages = state.get("messages", [])[-limit:]
    lines: list[str] = []
    for message in messages:
        text = (
            message.content
            if isinstance(message.content, str)
            else str(message.content)
        )
        if not text.strip():
            continue
        role = "사용자" if isinstance(message, HumanMessage) else "네비게이터"
        lines.append(f"{role}: {text.strip()}")
    return "\n".join(lines)


def to_gemini_contents(messages: list[BaseMessage]) -> list[types.Content]:
    """LangGraph messages를 Gemini contents(role: user/model)로 변환한다."""
    contents: list[types.Content] = []
    for message in messages:
        text = (
            message.content
            if isinstance(message.content, str)
            else str(message.content)
        )
        if not text.strip():
            continue
        role = "user" if isinstance(message, HumanMessage) else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return contents
