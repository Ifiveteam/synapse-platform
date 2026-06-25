"""Archiver search 스텝 — 검색 쿼리 조립 (도메인 하드코딩 없음)."""

from __future__ import annotations

import re

from app.agents.archiver.models import ArchiverState, get_context_dom, wants_page_context
from app.agents.archiver.utils.context_refine import (
    clean_context_title,
    extract_url_search_hint,
    is_thin_context_body,
)

_REVIEW_HINT = re.compile(r"후기|리뷰|평점|평가|방문|추천|어때", re.IGNORECASE)
_INFO_HINT = re.compile(r"정보|소개|메뉴|가격|영업|위치|주소|특징|요약", re.IGNORECASE)


def _compose_search_query(
    *,
    title: str,
    url_hint: str,
    message: str,
    wants_reviews: bool,
    wants_info: bool,
) -> str:
    lead_parts: list[str] = []

    if title:
        if wants_reviews:
            lead_parts.append(f"{title} 후기 리뷰")
        elif wants_info:
            lead_parts.append(f"{title} 정보")
        else:
            lead_parts.append(title)

    if url_hint and url_hint.lower() not in title.lower():
        lead_parts.append(url_hint)

    lead = " ".join(lead_parts).strip()
    if lead and lead.lower() not in message.lower():
        return f"{lead}\n\n{message}"
    return message


def build_search_user_content(state: ArchiverState, user_message: str) -> str:
    """페이지 본문이 빈약하거나 BASIC DOM 폴백일 때 제목·URL을 검색 쿼리에 보강한다."""
    message = user_message.strip()
    if not message:
        return message

    title = clean_context_title(state.get("context_title"))
    url_hint = extract_url_search_hint(state.get("context_url"))
    context_body = get_context_dom(state)
    thin_body = is_thin_context_body(context_body)
    wants_reviews = bool(_REVIEW_HINT.search(message))
    wants_info = bool(_INFO_HINT.search(message))

    basic_dom_fallback = wants_page_context(state) and thin_body
    should_enrich = bool(title) and (thin_body or basic_dom_fallback)

    if not should_enrich:
        return message

    return _compose_search_query(
        title=title,
        url_hint=url_hint,
        message=message,
        wants_reviews=wants_reviews,
        wants_info=wants_info,
    )
