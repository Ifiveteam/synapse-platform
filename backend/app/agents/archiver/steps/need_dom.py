"""need_dom 스텝 — BASIC 경로에서 클라이언트 DOM 본문이 필요할 때 SSE 신호를 방출한다."""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.protocols.stream_status import need_dom_event
from app.agents.archiver.trace import log_node_enter
from app.agents.archiver.models import ArchiverState


async def need_dom(state: ArchiverState) -> dict[str, Any]:
    """context_body 없이 BASIC으로 분류된 경우 익스텐션에 DOM 수집을 요청한다."""
    log_node_enter("need_dom", state=state)

    writer = get_stream_writer()
    writer(need_dom_event())

    return {"current_step": "need_dom"}
