"""Archiver 세션 스크랩 컨텍스트 저장소 — LangGraph State 환류 SSOT.

채팅 히스토리는 DB가 SSOT이므로, 스크랩 본문·요약만 세션별로 인메모리에 보관한다.
(LangGraph checkpointer에 묶으면 astream마다 thread_id가 필수이고 메시지가 중복 누적된다.)
"""

from __future__ import annotations

from typing import Any, TypedDict


class ScrappedSessionContext(TypedDict, total=False):
    scrapped_content: str
    scrapped_summary: str
    page_scrap_completed: bool


_scrapped_by_session: dict[str, ScrappedSessionContext] = {}


def save_scrapped_session_context(
    session_id: str,
    *,
    scrapped_content: str,
    scrapped_summary: str,
) -> None:
    """POST /scraps 완료 시 세션별 스크랩 컨텍스트를 저장한다."""
    body = scrapped_content.strip()
    if not body:
        return
    _scrapped_by_session[session_id] = {
        "scrapped_content": body,
        "scrapped_summary": scrapped_summary.strip(),
        "page_scrap_completed": True,
    }


def load_scrapped_session_context(session_id: str) -> dict[str, Any]:
    """세션에 환류된 스크랩 컨텍스트를 조회한다."""
    stored = _scrapped_by_session.get(session_id)
    if not stored:
        return {}
    return dict(stored)
