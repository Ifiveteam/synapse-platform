"""외부 실시간 트렌드 데이터 수집 서비스."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, TypedDict

import feedparser
import httpx

logger = logging.getLogger(__name__)

GOOGLE_TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=KR"
YOUTUBE_TRENDING_API_URL = "https://www.googleapis.com/youtube/v3/videos"
NAVER_REALTIME_PRIMARY_URL = "https://api.signal.bz/news/realtime"
NAVER_REALTIME_FALLBACK_URL = "https://api.isignal.co/news/realtime"
NAVER_SEARCH_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.xml"

YOUTUBE_API_KEY_ENV_VAR = "YOUTUBE_API_KEY"
NAVER_CLIENT_ID_ENV_VAR = "NAVER_CLIENT_ID"
NAVER_CLIENT_SECRET_ENV_VAR = "NAVER_CLIENT_SECRET"

HTTP_TIMEOUT_SECONDS = 15.0
GOOGLE_TRENDS_LIMIT = 10
YOUTUBE_TRENDING_LIMIT = 10
NAVER_SEARCH_LIMIT = 10
NAVER_NEWS_LIMIT = 12

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

_YOUTUBE_CATEGORY_BY_ID: dict[str, str] = {
    "1": "영화/애니메이션",
    "2": "자동차",
    "10": "음악",
    "15": "애완동물",
    "17": "스포츠",
    "19": "여행/이벤트",
    "20": "게임",
    "22": "인물/블로그",
    "23": "코미디",
    "24": "엔터테인먼트",
    "25": "뉴스/정치",
    "26": "하우투/스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "비영리/사회운동",
}

_NEWS_RSS_FEEDS: tuple[tuple[str, str, str], ...] = (
    ("politics", "정치", "https://www.yna.co.kr/rss/politics.xml"),
    ("economy", "경제", "https://www.yna.co.kr/rss/economy.xml"),
    ("society", "사회", "https://www.yna.co.kr/rss/society.xml"),
    ("it_science", "IT/과학", "https://www.yna.co.kr/rss/industry.xml"),
)

_NAVER_OPENAPI_SECTION_QUERIES: tuple[tuple[str, str], ...] = (
    ("정치", "정치"),
    ("경제", "경제"),
    ("사회", "사회"),
    ("IT 과학", "IT/과학"),
)

class GoogleTrendItem(TypedDict):
    keyword: str
    rank: int
    interest_index: int
    wow_change_pct: float


class YouTubeTrendItem(TypedDict):
    keyword: str
    rank: int
    category: str
    estimated_views: int


class NaverSearchTrendItem(TypedDict):
    keyword: str
    rank: int
    search_volume_hint: int
    state: str


class NaverNewsTrendItem(TypedDict):
    headline: str
    rank: int
    press: str
    section: str
    published_at: str
    link: str


class ExternalMarketTrends(TypedDict):
    google_trends: list[GoogleTrendItem]
    youtube_trending: list[YouTubeTrendItem]
    naver_search: list[NaverSearchTrendItem]
    naver_news: list[NaverNewsTrendItem]
    data_collected_at: str


def _parse_approx_traffic(traffic: str) -> int:
    """Google Trends RSS의 approx_traffic 문자열(예: '2000+')을 정수 지수로 변환한다."""
    match = re.search(r"(\d+)", traffic)
    if not match:
        return 50
    return int(match.group(1))


def _extract_ht_field(entry: Any, field_name: str) -> str:
    """feedparser 엔트리에서 ht 네임스페이스 필드를 안전하게 읽는다."""
    ht_namespace = getattr(entry, "ht_approx_traffic", None)
    if field_name == "approx_traffic" and ht_namespace is not None:
        return str(ht_namespace)

    for key, value in entry.items():
        if key.endswith(field_name):
            return str(value)
    return ""


def _parse_google_trend_entry(entry: Any, rank: int) -> GoogleTrendItem:
    traffic_raw = _extract_ht_field(entry, "approx_traffic")
    interest_index = _parse_approx_traffic(traffic_raw) if traffic_raw else 50

    return {
        "keyword": str(entry.get("title", "")).strip(),
        "rank": rank,
        "interest_index": interest_index,
        "wow_change_pct": 0.0,
    }


def _resolve_youtube_category(category_id: str) -> str:
    return _YOUTUBE_CATEGORY_BY_ID.get(category_id, "엔터테인먼트")


def _extract_youtube_api_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error", {})
        if isinstance(error, dict):
            return str(error.get("message", "")).strip()
    except ValueError:
        pass
    return ""


def _log_youtube_api_failure(response: httpx.Response) -> None:
    status = response.status_code
    detail = _extract_youtube_api_error_message(response)

    if status == 403:
        logger.warning(
            "YouTube Data API 403 Forbidden%s. "
            "Google Cloud Console에서 YouTube Data API v3 활성화, "
            "API 키 애플리케이션 제한, 일일 쿼터를 확인하세요.",
            f": {detail}" if detail else "",
        )
        return

    logger.warning(
        "YouTube Data API 요청 실패: HTTP %s%s",
        status,
        f" — {detail}" if detail else "",
    )


def _parse_youtube_api_items(items: list[dict[str, Any]]) -> list[YouTubeTrendItem]:
    trending: list[YouTubeTrendItem] = []
    for index, item in enumerate(items[:YOUTUBE_TRENDING_LIMIT], start=1):
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        title = str(snippet.get("title", "")).strip()
        if not title:
            continue

        view_count_raw = statistics.get("viewCount", "0")
        try:
            estimated_views = int(view_count_raw)
        except (TypeError, ValueError):
            estimated_views = 0

        trending.append(
            {
                "keyword": title,
                "rank": index,
                "category": _resolve_youtube_category(
                    str(snippet.get("categoryId", ""))
                ),
                "estimated_views": estimated_views,
            }
        )
    return trending


def _parse_naver_realtime_payload(
    payload: dict[str, Any],
) -> list[NaverSearchTrendItem]:
    bucket = payload.get("top10") or payload.get("top20") or payload.get("data") or []
    if not isinstance(bucket, list):
        return []

    trending: list[NaverSearchTrendItem] = []
    for index, item in enumerate(bucket[:NAVER_SEARCH_LIMIT], start=1):
        if not isinstance(item, dict):
            continue

        keyword = str(item.get("keyword") or item.get("title") or "").strip()
        if not keyword:
            continue

        rank_raw = item.get("rank", index)
        try:
            rank = int(rank_raw)
        except (TypeError, ValueError):
            rank = index

        count_raw = item.get("count") or item.get("traffic") or item.get("volume") or 0
        try:
            search_volume_hint = int(count_raw)
        except (TypeError, ValueError):
            search_volume_hint = max(NAVER_SEARCH_LIMIT - index + 1, 1) * 10

        trending.append(
            {
                "keyword": keyword,
                "rank": rank,
                "search_volume_hint": search_volume_hint,
                "state": str(item.get("state", "n")),
            }
        )
    return trending


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_rss_published_at(entry: Any) -> str:
    published_raw = str(entry.get("published", "")).strip()
    if not published_raw:
        return datetime.now(tz=UTC).isoformat()

    try:
        return parsedate_to_datetime(published_raw).astimezone(UTC).isoformat()
    except (TypeError, ValueError, OverflowError):
        return published_raw


def _extract_press_name(entry: Any) -> str:
    source = entry.get("source")
    if isinstance(source, dict):
        title = str(source.get("title", "")).strip()
        if title:
            return title

    author = str(entry.get("author", "")).strip()
    if author:
        return author

    return "미상"


def _parse_news_feed_entries(
    feed_text: str,
    *,
    section_key: str,
    section_label: str,
    per_feed_limit: int = 3,
) -> list[NaverNewsTrendItem]:
    feed = feedparser.parse(feed_text)
    items: list[NaverNewsTrendItem] = []

    for entry in feed.entries[:per_feed_limit]:
        headline = _strip_html(str(entry.get("title", "")).strip())
        if not headline:
            continue

        items.append(
            {
                "headline": headline,
                "rank": 0,
                "press": _extract_press_name(entry),
                "section": section_label,
                "published_at": _parse_rss_published_at(entry),
                "link": str(entry.get("link", "")).strip(),
            }
        )

    return items


async def _fetch_rss_feed_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await client.get(url)
        if response.status_code != 200 or not response.text.strip():
            return None
        return response.text
    except httpx.HTTPError:
        return None


async def _fetch_naver_openapi_news(
    client: httpx.AsyncClient,
    *,
    query: str,
    section_label: str,
    per_query_limit: int = 2,
) -> list[NaverNewsTrendItem]:
    client_id = os.getenv(NAVER_CLIENT_ID_ENV_VAR)
    client_secret = os.getenv(NAVER_CLIENT_SECRET_ENV_VAR)
    if not client_id or not client_secret:
        return []

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": per_query_limit,
        "start": 1,
        "sort": "date",
    }

    try:
        response = await client.get(
            NAVER_SEARCH_NEWS_API_URL,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    return _parse_news_feed_entries(
        response.text,
        section_key=query,
        section_label=section_label,
        per_feed_limit=per_query_limit,
    )


async def fetch_google_trending_keywords() -> list[GoogleTrendItem]:
    """Google Trends 대한민국 RSS에서 실시간 급상승 키워드를 수집한다."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(GOOGLE_TRENDS_RSS_URL)
        response.raise_for_status()

    feed = feedparser.parse(response.text)
    entries = feed.entries[:GOOGLE_TRENDS_LIMIT]

    return [
        _parse_google_trend_entry(entry, rank=index)
        for index, entry in enumerate(entries, start=1)
        if str(entry.get("title", "")).strip()
    ]


async def fetch_youtube_trending_videos() -> list[YouTubeTrendItem]:
    """YouTube Data API로 급상승 동영상을 수집한다.

    API 키가 없거나 요청이 실패하면 빈 목록을 반환한다.
    403 시 Cloud Console 설정 안내를 로그에 남긴다.
    """
    api_key = os.getenv(YOUTUBE_API_KEY_ENV_VAR)
    if not api_key:
        logger.warning(
            "%s가 설정되지 않아 YouTube 급상승 데이터를 수집하지 않습니다.",
            YOUTUBE_API_KEY_ENV_VAR,
        )
        return []

    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": "KR",
        "maxResults": YOUTUBE_TRENDING_LIMIT,
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(YOUTUBE_TRENDING_API_URL, params=params)
            if response.is_error:
                _log_youtube_api_failure(response)
                return []
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("YouTube Data API 네트워크 오류: %s", exc)
        return []
    except ValueError as exc:
        logger.warning("YouTube Data API 응답 파싱 실패: %s", exc)
        return []

    items = payload.get("items", [])
    if not items:
        logger.warning("YouTube Data API가 급상승 항목을 반환하지 않았습니다.")
        return []

    return _parse_youtube_api_items(items)


async def fetch_naver_trending_keywords() -> list[NaverSearchTrendItem]:
    """네이버 기준 실시간 핫 키워드를 수집한다.

    시그널(signal.bz) 공개 API를 우선 사용하고,
    실패 시 isignal 대안 엔드포인트를 시도한다.
    """
    endpoints = (NAVER_REALTIME_PRIMARY_URL, NAVER_REALTIME_FALLBACK_URL)

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT_SECONDS,
        headers=_BROWSER_HEADERS,
    ) as client:
        for endpoint in endpoints:
            try:
                response = await client.get(endpoint)
                response.raise_for_status()
                parsed = _parse_naver_realtime_payload(response.json())
                if parsed:
                    return parsed
            except (httpx.HTTPError, ValueError, TypeError):
                continue

    return []


async def fetch_naver_news_trends() -> list[NaverNewsTrendItem]:
    """연합뉴스 섹션 RSS와(부족 시) 네이버 검색 Open API로 주요 헤드라인을 수집한다."""
    collected: list[NaverNewsTrendItem] = []

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT_SECONDS,
        headers=_BROWSER_HEADERS,
        follow_redirects=True,
    ) as client:
        for _section_key, section_label, feed_url in _NEWS_RSS_FEEDS:
            feed_text = await _fetch_rss_feed_text(client, feed_url)
            if feed_text:
                collected.extend(
                    _parse_news_feed_entries(
                        feed_text,
                        section_key=_section_key,
                        section_label=section_label,
                    )
                )

        if len(collected) < NAVER_NEWS_LIMIT // 2:
            has_openapi = bool(
                os.getenv(NAVER_CLIENT_ID_ENV_VAR)
                and os.getenv(NAVER_CLIENT_SECRET_ENV_VAR)
            )
            if not has_openapi:
                logger.info(
                    "뉴스 RSS 수집이 부족합니다(%s건). %s/%s 설정 시 "
                    "네이버 검색 Open API로 보완합니다.",
                    len(collected),
                    NAVER_CLIENT_ID_ENV_VAR,
                    NAVER_CLIENT_SECRET_ENV_VAR,
                )
            for query, section_label in _NAVER_OPENAPI_SECTION_QUERIES:
                collected.extend(
                    await _fetch_naver_openapi_news(
                        client,
                        query=query,
                        section_label=section_label,
                    )
                )

    if not collected:
        return []

    deduped: list[NaverNewsTrendItem] = []
    seen_headlines: set[str] = set()
    for item in collected:
        headline_key = item["headline"].casefold()
        if headline_key in seen_headlines:
            continue
        seen_headlines.add(headline_key)
        deduped.append(item)

    deduped.sort(key=lambda row: row["published_at"], reverse=True)
    limited = deduped[:NAVER_NEWS_LIMIT]

    return [
        {**item, "rank": index}
        for index, item in enumerate(limited, start=1)
    ]


async def fetch_real_trends() -> ExternalMarketTrends:
    """Google·YouTube·네이버 외부 트렌드 소스를 병렬 수집해 통합 객체로 반환한다."""
    (
        google_trends,
        youtube_trending,
        naver_search,
        naver_news,
    ) = await asyncio.gather(
        fetch_google_trending_keywords(),
        fetch_youtube_trending_videos(),
        fetch_naver_trending_keywords(),
        fetch_naver_news_trends(),
    )

    return {
        "google_trends": google_trends,
        "youtube_trending": youtube_trending,
        "naver_search": naver_search,
        "naver_news": naver_news,
        "data_collected_at": datetime.now(tz=UTC).isoformat(),
    }
