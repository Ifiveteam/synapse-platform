"""외부 거시 시장 트렌드 수집기 — 네이버 데이터랩·구글 트렌드 RSS.

Phase 2-4: 수집 데이터를 6대 TrendDomain 체계로 정규화하여
GlobalTrendsSnapshot.external_market_keywords JSONB에 적재한다.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from typing import Any, TypeVar

import aiohttp

from app.agents.aggregator.utils.aggregator_logger import AggregatorLogger
from app.models.trend_domain import TrendDomain
from app.repositories.aggregator_repository import KST

_logger = logging.getLogger("app.services.external_trend_service")

# --- API 엔드포인트 ---
NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
GOOGLE_TRENDS_DAILY_RSS_URL = "https://trends.google.com/trending/rss?geo=KR"

NAVER_CLIENT_ID_ENV = "NAVER_CLIENT_ID"
NAVER_CLIENT_SECRET_ENV = "NAVER_CLIENT_SECRET"

HTTP_TIMEOUT_SECONDS = float(os.getenv("EXTERNAL_TREND_HTTP_TIMEOUT", "15"))
HTTP_MAX_RETRIES = int(os.getenv("EXTERNAL_TREND_MAX_RETRIES", "3"))
HTTP_RETRY_BASE_DELAY = float(os.getenv("EXTERNAL_TREND_RETRY_DELAY", "1.5"))
GOOGLE_TRENDS_LIMIT = int(os.getenv("EXTERNAL_TREND_GOOGLE_LIMIT", "20"))
NAVER_LOOKBACK_DAYS = int(os.getenv("EXTERNAL_TREND_NAVER_LOOKBACK_DAYS", "7"))

# 네이버 데이터랩 keywordGroups — 도메인당 대표 주제어 (최대 5그룹/요청)
_DOMAIN_NAVER_KEYWORDS: dict[TrendDomain, list[str]] = {
    TrendDomain.TECH_BUSINESS: ["인공지능", "스타트업", "반도체", "빅테크"],
    TrendDomain.CONTENT_MEDIA: ["넷플릭스", "유튜브", "KPOP", "드라마"],
    TrendDomain.LIFESTYLE_WELLNESS: ["다이어트", "운동", "뷰티", "건강"],
    TrendDomain.SOCIAL_CURRENT_AFFAIRS: ["정치", "사회", "선거", "국회"],
    TrendDomain.KNOWLEDGE_EDUCATION: ["자격증", "온라인강의", "영어공부", "수능"],
    TrendDomain.ECONOMY_TECHFIN: ["주식", "비트코인", "금리", "부동산"],
}

# 구글 RSS 키워드 → 도메인 휴리스틱 분류용 시드
_DOMAIN_CLASSIFY_SEEDS: dict[TrendDomain, tuple[str, ...]] = {
    TrendDomain.TECH_BUSINESS: (
        "ai",
        "인공지능",
        "스타트업",
        "반도체",
        "테크",
        "it",
        "앱",
        "개발",
        "삼성",
        "애플",
        "chatgpt",
    ),
    TrendDomain.CONTENT_MEDIA: (
        "넷플릭스",
        "유튜브",
        "kpop",
        "드라마",
        "영화",
        "예능",
        "아이돌",
        "방송",
        "음악",
    ),
    TrendDomain.LIFESTYLE_WELLNESS: (
        "다이어트",
        "운동",
        "뷰티",
        "건강",
        "여행",
        "맛집",
        "패션",
        "웰니스",
    ),
    TrendDomain.SOCIAL_CURRENT_AFFAIRS: (
        "정치",
        "사회",
        "선거",
        "국회",
        "대통령",
        "뉴스",
        "사건",
        "재판",
    ),
    TrendDomain.KNOWLEDGE_EDUCATION: (
        "자격증",
        "강의",
        "영어",
        "수능",
        "교육",
        "공부",
        "대학",
        "채용",
    ),
    TrendDomain.ECONOMY_TECHFIN: (
        "주식",
        "비트코인",
        "금리",
        "부동산",
        "경제",
        "환율",
        "코인",
        "etf",
        "투자",
    ),
}

_GOOGLE_RSS_NS = {"ht": "https://trends.google.com/trending/rss"}
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

T = TypeVar("T")


def _empty_domain_buckets() -> dict[str, dict[str, Any]]:
    """6대 도메인별 빈 수집 버킷."""
    return {
        domain.value: {
            "naver": [],
            "google": [],
            "domain_score": 0.0,
        }
        for domain in TrendDomain
    }


def _parse_approx_traffic(traffic: str | None) -> int:
    """구글 RSS approx_traffic 문자열(예: '2000+')을 정수 지수로 변환."""
    if not traffic:
        return 50
    match = re.search(r"(\d+)", traffic)
    if not match:
        return 50
    return int(match.group(1))


def _classify_google_keyword(keyword: str) -> TrendDomain:
    """급상승 키워드를 6대 TrendDomain 중 하나로 휴리스틱 분류."""
    lowered = keyword.lower()
    best_domain = TrendDomain.SOCIAL_CURRENT_AFFAIRS
    best_score = 0

    for domain, seeds in _DOMAIN_CLASSIFY_SEEDS.items():
        score = sum(1 for seed in seeds if seed in lowered)
        if score > best_score:
            best_score = score
            best_domain = domain

    return best_domain


def _datalab_date_range(target: date) -> tuple[str, str]:
    """배치 기준일을 포함한 네이버 데이터랩 조회 구간 (yyyy-MM-dd)."""
    end = target
    start = target - timedelta(days=max(NAVER_LOOKBACK_DAYS - 1, 1))
    return start.isoformat(), end.isoformat()


def _build_naver_request_batches(
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """네이버 API 제한(최대 5 keywordGroups/요청)에 맞춰 6도메인을 2회로 분할."""
    all_groups = [
        {
            "groupName": domain.value,
            "keywords": keywords,
        }
        for domain, keywords in _DOMAIN_NAVER_KEYWORDS.items()
    ]
    batches: list[dict[str, Any]] = []
    chunk_size = 5
    for index in range(0, len(all_groups), chunk_size):
        batches.append(
            {
                "startDate": start_date,
                "endDate": end_date,
                "timeUnit": "date",
                "keywordGroups": all_groups[index : index + chunk_size],
            }
        )
    return batches


def _parse_naver_datalab_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """네이버 데이터랩 응답 → 정규화된 키워드·지수 리스트."""
    parsed: list[dict[str, Any]] = []
    results = payload.get("results")
    if not isinstance(results, list):
        return parsed

    for group in results:
        if not isinstance(group, dict):
            continue
        group_name = str(group.get("title") or group.get("groupName") or "").strip()
        keywords = group.get("keywords")
        keyword_label = (
            ", ".join(keywords) if isinstance(keywords, list) else group_name
        )
        data_points = group.get("data")
        if not isinstance(data_points, list) or not data_points:
            continue

        latest = data_points[-1]
        if not isinstance(latest, dict):
            continue

        period = str(latest.get("period", ""))
        ratio_raw = latest.get("ratio", 0)
        try:
            score = float(ratio_raw)
        except (TypeError, ValueError):
            score = 0.0

        domain = _resolve_domain_from_group_name(group_name)
        parsed.append(
            {
                "domain": domain.value,
                "group_name": group_name,
                "keywords": keyword_label,
                "period": period,
                "score": round(score, 2),
            }
        )

    return parsed


def _resolve_domain_from_group_name(group_name: str) -> TrendDomain:
    """groupName이 TrendDomain.value와 일치하면 해당 도메인 반환."""
    for domain in TrendDomain:
        if domain.value == group_name:
            return domain
    return TrendDomain.SOCIAL_CURRENT_AFFAIRS


def _parse_google_daily_rss(xml_text: str) -> list[dict[str, Any]]:
    """구글 일별 급상승 RSS XML → 키워드·순위·approx_traffic 리스트."""
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        msg = f"구글 RSS XML 파싱 실패: {exc}"
        raise ValueError(msg) from exc

    for rank, item in enumerate(root.findall(".//item"), start=1):
        if rank > GOOGLE_TRENDS_LIMIT:
            break

        title = (item.findtext("title") or "").strip()
        if not title:
            continue

        traffic_el = item.find("ht:approx_traffic", _GOOGLE_RSS_NS)
        if traffic_el is None:
            traffic_el = item.find(
                "{https://trends.google.com/trending/rss}approx_traffic"
            )
        approx_traffic = _parse_approx_traffic(
            traffic_el.text if traffic_el is not None else None
        )

        pub_date = (item.findtext("pubDate") or "").strip()
        domain = _classify_google_keyword(title)

        items.append(
            {
                "domain": domain.value,
                "keyword": title,
                "rank": rank,
                "approx_traffic": approx_traffic,
                "published_at": pub_date,
            }
        )

    return items


def _merge_into_domain_buckets(
    by_domain: dict[str, dict[str, Any]],
    *,
    naver_items: list[dict[str, Any]],
    google_items: list[dict[str, Any]],
) -> None:
    """정규화된 원천 데이터를 도메인별 버킷에 병합하고 composite score 산출."""
    for item in naver_items:
        domain_key = item.get("domain")
        if domain_key not in by_domain:
            continue
        by_domain[domain_key]["naver"].append(
            {
                "keywords": item.get("keywords"),
                "group_name": item.get("group_name"),
                "period": item.get("period"),
                "score": item.get("score"),
            }
        )

    for item in google_items:
        domain_key = item.get("domain")
        if domain_key not in by_domain:
            continue
        by_domain[domain_key]["google"].append(
            {
                "keyword": item.get("keyword"),
                "rank": item.get("rank"),
                "approx_traffic": item.get("approx_traffic"),
                "published_at": item.get("published_at"),
            }
        )

    for bucket in by_domain.values():
        naver_scores = [
            float(entry["score"])
            for entry in bucket["naver"]
            if isinstance(entry.get("score"), (int, float))
        ]
        google_scores = [
            float(entry["approx_traffic"])
            for entry in bucket["google"]
            if isinstance(entry.get("approx_traffic"), (int, float))
        ]

        components: list[float] = []
        if naver_scores:
            components.append(sum(naver_scores) / len(naver_scores))
        if google_scores:
            components.append(sum(google_scores) / len(google_scores))

        bucket["domain_score"] = (
            round(sum(components) / len(components), 2) if components else 0.0
        )


class ExternalTrendService:
    """네이버 데이터랩·구글 트렌드 RSS 비동기 수집 및 6대 도메인 정규화."""

    def __init__(self, agg_logger: AggregatorLogger | None = None) -> None:
        self._agg_logger = agg_logger or AggregatorLogger()
        self._timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)

    async def collect_market_keywords(
        self,
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """외부 트렌드를 수집·도메인 매핑한 JSONB 적재 규격 dict 반환.

        개별 소스 장애 시 해당 소스만 빈 리스트로 두고 나머지는 계속 진행한다.
        """
        batch_date = target_date or (datetime.now(KST).date() - timedelta(days=1))
        collected_at = datetime.now(KST).isoformat()

        naver_items: list[dict[str, Any]] = []
        google_items: list[dict[str, Any]] = []
        status: dict[str, str] = {
            "naver_datalab": "skipped",
            "google_rss": "skipped",
        }

        naver_items, naver_status = await self._fetch_naver_datalab_safe(batch_date)
        status["naver_datalab"] = naver_status

        google_items, google_status = await self._fetch_google_rss_safe()
        status["google_rss"] = google_status

        if naver_status != "ok" and google_status != "ok":
            _logger.warning(
                "[external_trend] 모든 외부 소스 수집 실패 — naver=%s google=%s",
                naver_status,
                google_status,
            )
            return {}

        by_domain = _empty_domain_buckets()
        _merge_into_domain_buckets(
            by_domain,
            naver_items=naver_items,
            google_items=google_items,
        )

        return {
            "data_collected_at": collected_at,
            "target_date": batch_date.isoformat(),
            "collection_status": status,
            "by_domain": by_domain,
            "raw": {
                "naver_datalab": naver_items,
                "google_trends": google_items,
            },
        }

    async def collect_market_keywords_safe(
        self,
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """배치 파이프라인용 fault-tolerant 래퍼 — 예외 시 {} 반환."""
        try:
            return await self.collect_market_keywords(target_date=target_date)
        except Exception as exc:
            _logger.exception(
                "[external_trend] collect_market_keywords 치명적 오류 — "
                "빈 dict 반환 error=%s",
                exc,
            )
            self._agg_logger.log_failure(
                "behavior",
                "llm",
                operation="external_trends",
                latency_ms=0.0,
                error=exc,
            )
            return {}

    async def _fetch_naver_datalab_safe(
        self,
        target_date: date,
    ) -> tuple[list[dict[str, Any]], str]:
        """네이버 데이터랩 수집 — 실패 시 ([], status)."""
        client_id = os.getenv(NAVER_CLIENT_ID_ENV)
        client_secret = os.getenv(NAVER_CLIENT_SECRET_ENV)
        if not client_id or not client_secret:
            _logger.warning(
                "[external_trend][naver] %s/%s 미설정 — 스킵",
                NAVER_CLIENT_ID_ENV,
                NAVER_CLIENT_SECRET_ENV,
            )
            return [], "missing_credentials"

        start_date, end_date = _datalab_date_range(target_date)
        request_batches = _build_naver_request_batches(start_date, end_date)
        merged: list[dict[str, Any]] = []

        try:
            async with aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            ) as session:
                for batch_index, body in enumerate(request_batches, start=1):
                    batch_items = await self._request_with_retry(
                        lambda b=body: self._post_naver_datalab(
                            session,
                            client_id,
                            client_secret,
                            b,
                        ),
                        source=f"naver_datalab_batch_{batch_index}",
                    )
                    merged.extend(batch_items)

            _logger.info(
                "[external_trend][naver] 수집 완료 items=%d range=[%s, %s]",
                len(merged),
                start_date,
                end_date,
            )
            return merged, "ok"
        except Exception as exc:
            _logger.exception(
                "[external_trend][naver] 수집 실패 — 격리 후 스킵 error=%s",
                exc,
            )
            self._agg_logger.log_failure(
                "behavior",
                "llm",
                operation="naver_datalab",
                latency_ms=0.0,
                error=exc,
            )
            return [], "error"

    async def _post_naver_datalab(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        body: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """단일 네이버 데이터랩 POST 요청."""
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json",
        }
        async with session.post(
            NAVER_DATALAB_URL,
            json=body,
            headers=headers,
        ) as response:
            response_text = await response.text()
            if response.status == 429:
                msg = "네이버 데이터랩 Rate Limit (429)"
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=429,
                    message=msg,
                    headers=response.headers,
                )
            if response.status == 401:
                msg = "네이버 데이터랩 인증 실패 (401)"
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=401,
                    message=msg,
                    headers=response.headers,
                )
            if response.status >= 400:
                msg = f"네이버 데이터랩 HTTP {response.status}: {response_text[:300]}"
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=msg,
                    headers=response.headers,
                )

            payload = await response.json()
            if not isinstance(payload, dict):
                msg = "네이버 데이터랩 응답이 JSON object가 아님"
                raise TypeError(msg)
            return _parse_naver_datalab_response(payload)

    async def _fetch_google_rss_safe(self) -> tuple[list[dict[str, Any]], str]:
        """구글 일별 급상승 RSS 수집 — 실패 시 ([], status)."""
        try:
            items = await self._request_with_retry(
                self._fetch_google_daily_rss,
                source="google_rss",
            )
            _logger.info(
                "[external_trend][google] 수집 완료 items=%d",
                len(items),
            )
            return items, "ok"
        except Exception as exc:
            _logger.exception(
                "[external_trend][google] 수집 실패 — 격리 후 스킵 error=%s",
                exc,
            )
            self._agg_logger.log_failure(
                "behavior",
                "llm",
                operation="google_rss",
                latency_ms=0.0,
                error=exc,
            )
            return [], "error"

    async def _fetch_google_daily_rss(self) -> list[dict[str, Any]]:
        """구글 트렌드 대한민국 일별 급상승 RSS 비동기 fetch·파싱."""
        async with aiohttp.ClientSession(
            timeout=self._timeout,
            headers=_BROWSER_HEADERS,
        ) as session:
            async with session.get(GOOGLE_TRENDS_DAILY_RSS_URL) as response:
                response_text = await response.text()
                if response.status >= 400:
                    msg = f"구글 RSS HTTP {response.status}: {response_text[:300]}"
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=msg,
                        headers=response.headers,
                    )
                return _parse_google_daily_rss(response_text)

    async def _request_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        source: str,
    ) -> T:
        """네트워크 I/O 재시도 가드 — 지수 백오프."""
        last_error: Exception | None = None

        for attempt in range(1, HTTP_MAX_RETRIES + 1):
            try:
                return await operation()
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                ValueError,
                TypeError,
            ) as exc:
                last_error = exc
                if attempt >= HTTP_MAX_RETRIES:
                    break
                delay = HTTP_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                _logger.warning(
                    "[external_trend][%s] 재시도 %d/%d delay=%.1fs error=%s",
                    source,
                    attempt,
                    HTTP_MAX_RETRIES,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error
