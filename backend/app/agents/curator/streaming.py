"""SSE 직렬화 — Archiver와 동일한 포맷."""

from __future__ import annotations

import json

from app.agents.curator.types import CuratorStreamEvent, StreamEventType


def format_sse(*, event: StreamEventType, content: str) -> str:
    payload = json.dumps({"content": content}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def format_stream_event(e: CuratorStreamEvent) -> str:
    return format_sse(event=e.event, content=e.content)
