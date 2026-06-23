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


class DataSource(StrEnum):
    PROFILE = "profile"               # 페르소나·성향 요약
    STATS = "stats"                   # 총 시청 수·카테고리 통계
    CHANNELS = "channels"             # 자주 본 채널 TOP 5
    RECENT = "recent"                 # 최근 시청 영상 (쇼츠 제외)
    SHORTS = "shorts"                 # 최근 본 쇼츠 영상
    VECTOR_CATALOG = "vector_catalog" # 질문 관련 영상 (벡터 검색)
    VECTOR_ANALYSIS = "vector_analysis" # 질문 관련 영상 분석 (벡터 검색)


class RouteDecision(BaseModel):
    route: Literal["MY_DATA", "GENERAL"] = Field(
        description="MY_DATA=유저 본인 데이터 필요, GENERAL=일반 지식으로 충분"
    )
    needed_sources: list[str] = Field(
        default_factory=list,
        description=(
            "MY_DATA일 때만 사용. 필요한 데이터 소스 목록. "
            "profile=성향/취향/페르소나, stats=시청 통계/카테고리/비율, "
            "channels=자주 본 채널, recent=최근/요즘 시청 영상(쇼츠 제외), "
            "shorts=최근 본 쇼츠(Shorts) 영상, "
            "vector_catalog=특정 주제 관련 영상 검색, vector_analysis=영상 내용 분석/요약"
        ),
    )


class CuratorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    user_id: uuid.UUID
    session_id: NotRequired[str]

    route: NotRequired[CuratorRoute]
    needed_sources: NotRequired[list[str]]
    retrieval_context: NotRequired[str]

    final_response: NotRequired[str]
    error: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


StreamEventType = Literal["status", "token", "chart"]


@dataclass(frozen=True, slots=True)
class CuratorStreamEvent:
    event: StreamEventType
    content: str
