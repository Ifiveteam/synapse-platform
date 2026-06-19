"""Archiver SSE 스트림 포맷 — event/data JSON envelope."""

from __future__ import annotations

import json

from app.agents.archiver.types import ArchiverStreamEvent, StreamEventType


def format_sse_event(*, event: StreamEventType, content: str) -> str:
    """표준 SSE 프레임 — `event:` + JSON `data:` (content 필드)."""
    payload = json.dumps({"content": content}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def format_stream_event(event: ArchiverStreamEvent) -> str:
    """ArchiverStreamEvent를 SSE 문자열로 직렬화한다."""
    return format_sse_event(event=event.event, content=event.content)
