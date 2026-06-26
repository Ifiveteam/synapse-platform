"""Archiver multi-turn 대화 메시지 빌더 (LangGraph 노드 아님)."""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.archiver.core.constants import MAX_HISTORY_MESSAGES
from app.schemas.archiver import ArchiverChatMessage


def history_to_messages(
    history: list[ArchiverChatMessage],
    *,
    limit: int = MAX_HISTORY_MESSAGES,
) -> list[BaseMessage]:
    """DB 히스토리를 LangGraph messages로 변환한다 (최근 N건만)."""
    trimmed = history[-limit:] if limit > 0 else history
    messages: list[BaseMessage] = []
    for item in trimmed:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
    return messages


def append_user_turn(
    messages: list[BaseMessage],
    user_message: str,
) -> list[BaseMessage]:
    """기존 히스토리 뒤에 새 user 턴을 붙인다."""
    return [*messages, HumanMessage(content=user_message)]
