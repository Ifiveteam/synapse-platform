"""Archiver SSE 스트림 포맷 — event/data JSON envelope."""

from __future__ import annotations

import json
from typing import Any

from app.agents.archiver.models import ArchiverStreamEvent, StreamEventType


def format_sse_event(
    *,
    event: StreamEventType,
    content: str,
    phase: str | None = None,
    engines: list[str] | None = None,
    message: str | None = None,
    action: str | None = None,
    custom_category: str | None = None,
) -> str:
    """표준 SSE 프레임 — `event:` + JSON `data:` (content 필수, status 구조화 필드 optional)."""
    payload: dict[str, Any] = {"content": content}
    if message is not None:
        payload["message"] = message
    if phase is not None:
        payload["phase"] = phase
    if engines:
        payload["engines"] = engines
    if action is not None:
        payload["action"] = action
    if custom_category is not None:
        payload["custom_category"] = custom_category
    body = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {body}\n\n"


def format_stream_event(event: ArchiverStreamEvent) -> str:
    """ArchiverStreamEvent를 SSE 문자열로 직렬화한다."""
    engines = list(event.engines) if event.engines else None
    return format_sse_event(
        event=event.event,
        content=event.content,
        phase=event.phase,
        engines=engines,
        message=event.message,
        action=event.action,
        custom_category=event.custom_category,
    )
