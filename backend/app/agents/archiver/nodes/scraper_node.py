"""scrape_web_context 노드 — 활성 탭 URL에서 본문을 실시간 수집한다."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.agents.archiver.prompt import NO_CONTEXT_URL
from app.agents.archiver.state import ArchiverState

logger = logging.getLogger(__name__)

_MAX_BODY_CHARS = 5_000
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}
_NOISE_TAGS = ("script", "style", "nav", "footer", "header")


def _is_scrapable_url(url: str | None) -> bool:
    return bool(url and url != NO_CONTEXT_URL and url.startswith("http"))


def is_scrapable_url(url: str | None) -> bool:
    """스크래핑 가능한 HTTP(S) URL인지 판별한다."""
    return _is_scrapable_url(url)


def _extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(_NOISE_TAGS):
        element.extract()

    main_content = soup.find("main") or soup.find("article") or soup.find("body")
    raw_text = (
        main_content.get_text(separator="\n", strip=True)
        if main_content
        else soup.get_text(separator="\n", strip=True)
    )
    cleaned = "\n".join(
        line.strip() for line in raw_text.splitlines() if line.strip()
    )
    if len(cleaned) > _MAX_BODY_CHARS:
        return cleaned[:_MAX_BODY_CHARS]
    return cleaned


async def scrape_web_context_node(state: ArchiverState) -> dict[str, Any]:
    """사용자가 대화 중인 웹페이지 URL 본문을 긁어와 context_body에 적재한다."""
    url = state.get("context_url", "")
    if not _is_scrapable_url(url):
        return {
            "context_body": "스크래핑할 수 없는 유효하지 않은 도메인입니다.",
        }

    try:
        async with httpx.AsyncClient(
            timeout=6.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url, headers=_BROWSER_HEADERS)

            if response.status_code != 200:
                return {
                    "context_body": (
                        f"웹페이지에 접근할 수 없습니다. "
                        f"(Status Code: {response.status_code})"
                    ),
                }

            truncated_body = _extract_main_text(response.text)
            if not truncated_body:
                return {
                    "context_body": "웹페이지 본문을 추출하지 못했습니다.",
                }
            return {"context_body": truncated_body}

    except Exception:
        logger.exception("Archiver scraper node failed for url=%s", url)
        return {
            "context_body": "네트워크 문제로 웹페이지 본문을 분석하지 못했습니다.",
        }
