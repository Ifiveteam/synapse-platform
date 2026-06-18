"""활성 탭 URL 본문 스크래핑 — collect 노드에서 사용하는 비그래프 helper."""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from app.agents.archiver.constants import MAX_CONTEXT_BODY_CHARS
from app.agents.archiver.types import NO_CONTEXT_URL

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}
_NOISE_TAGS = ("script", "style", "nav", "footer", "header")


def is_scrapable_url(url: str | None) -> bool:
    """스크래핑 가능한 HTTP(S) URL인지 판별한다."""
    return bool(url and url != NO_CONTEXT_URL and url.startswith("http"))


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
    if len(cleaned) > MAX_CONTEXT_BODY_CHARS:
        return cleaned[:MAX_CONTEXT_BODY_CHARS]
    return cleaned


async def scrape_context_body(
    *,
    context_title: str,
    context_url: str,
) -> str:
    """사용자가 대화 중인 웹페이지 URL 본문을 긁어와 반환한다."""
    _ = context_title  # 향후 메타데이터 활용 여지
    if not is_scrapable_url(context_url):
        return "스크래핑할 수 없는 유효하지 않은 도메인입니다."

    try:
        async with httpx.AsyncClient(
            timeout=6.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(context_url, headers=_BROWSER_HEADERS)

            if response.status_code != 200:
                return (
                    f"웹페이지에 접근할 수 없습니다. "
                    f"(Status Code: {response.status_code})"
                )

            truncated_body = _extract_main_text(response.text)
            if not truncated_body:
                return "웹페이지 본문을 추출하지 못했습니다."
            return truncated_body

    except Exception:
        logger.exception("Archiver scraper failed for url=%s", context_url)
        return "네트워크 문제로 웹페이지 본문을 분석하지 못했습니다."
