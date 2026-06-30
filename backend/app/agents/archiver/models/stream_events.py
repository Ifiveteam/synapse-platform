"""Archiver SSE 스트림 이벤트 타입."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StreamEventType = Literal["status", "token", "need_dom", "action"]

StatusPhase = Literal[
    "router_general",
    "router_parallel",
    "collect",
    "rag",
    "search",
    "evaluator",
    "respond",
    "need_dom",
]


@dataclass(frozen=True, slots=True)
class ArchiverStreamEvent:
    """SSE 스트림 이벤트 — status(UI 안내)와 token(답변 본문)을 구분한다."""

    event: StreamEventType
    content: str
    phase: StatusPhase | None = None
    engines: tuple[str, ...] | None = None
    message: str | None = None
    action: str | None = None
    custom_category: str | None = None
