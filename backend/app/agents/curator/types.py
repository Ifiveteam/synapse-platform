"""Curator 타입 — Route, State, StreamEvent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class CuratorRoute(StrEnum):
    MY_DATA = "MY_DATA"    # 내 프로필·시청기록 기반
    GENERAL = "GENERAL"   # 일반 YouTube/콘텐츠 질문


class RouteDecision(BaseModel):
    route: Literal["MY_DATA", "GENERAL"] = Field(
        description="MY_DATA=유저 본인 데이터 필요, GENERAL=일반 지식으로 충분"
    )


class CuratorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    user_id: uuid.UUID
    session_id: NotRequired[str]

    route: NotRequired[CuratorRoute]
    retrieval_context: NotRequired[str]

    final_response: NotRequired[str]
    error: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


StreamEventType = Literal["status", "token"]


@dataclass(frozen=True, slots=True)
class CuratorStreamEvent:
    event: StreamEventType
    content: str
