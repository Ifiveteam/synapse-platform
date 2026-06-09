"""외부 실시간 트렌드 데이터 수집 서비스."""

from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, TypedDict

import feedparser
import httpx

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

_YOUTUBE_FALLBACK_TRENDING: tuple[tuple[str, str, int], ...] = (
    ("K-팝 신곡 챌린지", "음악", 4_200_000),
    ("AI 활용 꿀팁", "과학/기술", 1_850_000),
    ("프로야구 하이라이트", "스포츠", 3_100_000),
    ("넷플릭스 신작 리뷰", "엔터테인먼트", 2_640_000),
    ("주식 초보 가이드", "교육", 980_000),
    ("홈트 10분 루틴", "하우투/스타일", 1_420_000),
    ("인디 게임 플레이", "게임", 760_000),
    ("MZ 재테크 토크", "뉴스/정치", 1_150_000),
)

_NAVER_SEARCH_FALLBACK: tuple[tuple[str, int], ...] = (
    ("전세 사기 예방", 1),
    ("AI 스타트업", 2),
    ("프로야구 순위", 3),
    ("장마 대비", 4),
    ("반도체 실적", 5),
    ("총선 여론", 6),
    ("넷플릭스 신작", 7),
    ("비트코인 시세", 8),
)

_NAVER_NEWS_RSS_FEEDS: tuple[tuple[str, str, str], ...] = (
    ("politics", "정치", "https://news.naver.com/main/rss/section.naver?sid=101"),
    ("economy", "경제", "https://news.naver.com/main/rss/section.naver?sid=102"),
    ("society", "사회", "https://news.naver.com/main/rss/section.naver?sid=103"),
    ("it_science", "IT/과학", "https://news.naver.com/rss/sections/105.xml"),
)

_NAVER_NEWS_FALLBACK_FEEDS: tuple[tuple[str, str, str], ...] = (
    ("politics", "정치", "https://www.yna.co.kr/rss/politics.xml"),
    ("economy", "경제", "https://www.yna.co.kr/rss/economy.xml"),
    ("society", "사회", "https://www.yna.co.kr/rss/society.xml"),
    ("it_science", "IT/과학", "https://www.yna.co.kr/rss/industry.xml"),
)

_NAVER_NEWS_FALLBACK: tuple[tuple[str, str, str], ...] = (
    ("정부, 하반기 경기 부양책 검토", "연합뉴스", "경제"),
    ("AI 규제 프레임워크 논의 본격화", "한국경제", "IT/과학"),
    ("지방선거 이후 여야 정책 협상 주목", "조선일보", "정치"),
    ("장마 전 지역별 대비 점검 강화", "KBS", "사회"),
    ("2분기 실적 발표 주간, 증시 변동성 확대", "매일경제", "경제"),
    ("MZ세대 재테크 트렌드 리포트 공개", "머니투데이", "경제"),
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


def _build_youtube_fallback_trending() -> list[YouTubeTrendItem]:
    return [
        {
            "keyword": keyword,
            "rank": index,
            "category": category,
            "estimated_views": views,
        }
        for index, (keyword, category, views) in enumerate(
            _YOUTUBE_FALLBACK_TRENDING, start=1
        )
    ]


def _resolve_youtube_category(category_id: str) -> str:
    return _YOUTUBE_CATEGORY_BY_ID.get(category_id, "엔터테인먼트")


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


def _build_naver_search_fallback() -> list[NaverSearchTrendItem]:
    return [
        {
            "keyword": keyword,
            "rank": rank,
            "search_volume_hint": (NAVER_SEARCH_LIMIT - rank + 1) * 100,
            "state": "f",
        }
        for keyword, rank in _NAVER_SEARCH_FALLBACK
    ]


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


def _build_naver_news_fallback() -> list[NaverNewsTrendItem]:
    return [
        {
            "headline": headline,
            "rank": index,
            "press": press,
            "section": section,
            "published_at": datetime.now(tz=UTC).isoformat(),
            "link": "",
        }
        for index, (headline, press, section) in enumerate(
            _NAVER_NEWS_FALLBACK, start=1
        )
    ]


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

    API 키가 없거나 요청이 실패하면 Fallback 데이터를 반환한다.
    """
    api_key = os.getenv(YOUTUBE_API_KEY_ENV_VAR)
    if not api_key:
        return _build_youtube_fallback_trending()

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
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return _build_youtube_fallback_trending()

    items = payload.get("items", [])
    if not items:
        return _build_youtube_fallback_trending()

    parsed = _parse_youtube_api_items(items)
    return parsed or _build_youtube_fallback_trending()


async def fetch_naver_trending_keywords() -> list[NaverSearchTrendItem]:
    """네이버 기준 실시간 핫 키워드를 수집한다.

    시그널(signal.bz) 공개 API를 우선 사용하고,
    실패 시 isignal 대안·Fallback을 반환한다.
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

    return _build_naver_search_fallback()


async def fetch_naver_news_trends() -> list[NaverNewsTrendItem]:
    """네이버 뉴스 섹션 RSS(또는 대체 피드)에서 주요 헤드라인을 수집한다."""
    collected: list[NaverNewsTrendItem] = []

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT_SECONDS,
        headers=_BROWSER_HEADERS,
        follow_redirects=True,
    ) as client:
        for _section_key, section_label, feed_url in _NAVER_NEWS_RSS_FEEDS:
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
            for _section_key, section_label, feed_url in _NAVER_NEWS_FALLBACK_FEEDS:
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
            openapi_queries = (
                ("정치", "정치"),
                ("경제", "경제"),
                ("사회", "사회"),
                ("IT 과학", "IT/과학"),
            )
            for query, section_label in openapi_queries:
                collected.extend(
                    await _fetch_naver_openapi_news(
                        client,
                        query=query,
                        section_label=section_label,
                    )
                )

    if not collected:
        return _build_naver_news_fallback()

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
