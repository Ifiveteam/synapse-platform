"""Archiver LangGraph 스텝 공통 유틸."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.agents.archiver.types import ArchiverState


def latest_user_message(state: ArchiverState) -> str:
    """messages 스택에서 마지막 HumanMessage 본문을 추출한다."""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
    return ""
