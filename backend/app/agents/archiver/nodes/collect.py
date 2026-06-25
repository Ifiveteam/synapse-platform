"""collect_node — 익스텐션 DOM 또는 서버 스크래핑으로 페이지 본문을 수집한다."""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

from app.agents.archiver.utils.context_refine import (
    clean_context_title,
    clean_context_url,
    is_thin_context_body,
)
from app.agents.archiver.models import COLLECT_NODE, ArchiverState, get_context_dom
from app.agents.archiver.nodes.utils.scraper import (
    is_scrapable_url,
    is_usable_context_body,
    scrape_context_body,
)
from app.agents.archiver.protocols.stream_status import (
    MSG_DOM_COLLECTED,
    MSG_DOM_COLLECTING,
    MSG_DOM_SCRAPING,
    MSG_DOM_THIN_REVIEW,
    status_event,
)
from app.agents.archiver.trace import log_collect_result, log_node_enter


async def collect_node(state: ArchiverState) -> dict[str, Any]:
    """익스텐션 DOM 또는 서버 스크래핑으로 페이지 본문을 context_dom에 수집한다."""
    log_node_enter("collect_node", state=state)
    writer = get_stream_writer()
    patch: dict[str, Any] = {
        "current_step": COLLECT_NODE,
        "executed_steps": [COLLECT_NODE],
    }

    existing_body = get_context_dom(state)
    cleaned_title = clean_context_title(state.get("context_title"))
    cleaned_url = clean_context_url(state.get("context_url", ""))

    if cleaned_title:
        patch["context_title"] = cleaned_title
    if cleaned_url:
        patch["context_url"] = cleaned_url

    if is_usable_context_body(existing_body):
        writer(status_event(MSG_DOM_COLLECTED, phase="collect"))
        patch["context_dom"] = existing_body
        log_collect_result(
            route="BASIC",
            rag_chars=0,
            context_body_chars=len(existing_body),
            retrieval_attempts=state.get("retrieval_attempts", 0),
            rag_hit=False,
        )
        return patch

    writer(status_event(MSG_DOM_COLLECTING, phase="collect"))

    context_body = ""
    scrape_url = cleaned_url or state.get("context_url", "")

    if is_scrapable_url(scrape_url):
        writer(status_event(MSG_DOM_SCRAPING, phase="collect"))
        scraped = (
            await scrape_context_body(
                context_title=cleaned_title or state.get("context_title", ""),
                context_url=scrape_url,
            )
        ).strip()
        if is_usable_context_body(scraped):
            context_body = scraped
            writer(status_event(MSG_DOM_COLLECTED, phase="collect"))

    if is_thin_context_body(context_body):
        writer(status_event(MSG_DOM_THIN_REVIEW, phase="collect"))

    patch["context_dom"] = context_body
    log_collect_result(
        route="BASIC",
        rag_chars=0,
        context_body_chars=len(context_body),
        retrieval_attempts=state.get("retrieval_attempts", 0),
        rag_hit=False,
    )
    return patch
