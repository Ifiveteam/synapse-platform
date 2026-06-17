"""Archiver agent LangGraph state — chat history and tab context."""

from __future__ import annotations

from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ArchiverState(TypedDict):
    # 유저의 질문 및 입력 메시지 스택 (LangGraph 표준 add_messages 리듀서)
    messages: Annotated[list[BaseMessage], add_messages]

    # 프론트엔드가 실시간으로 밀어준 활성 탭 메타데이터
    context_title: str
    context_url: str

    # 백엔드가 직접 스크래핑하여 채집한 웹페이지 본문
    context_body: str

    # 파이프라인 오류 메시지 (있을 때만)
    error: NotRequired[str]
