"""Aggregator 파이프라인용 가상 통합 데이터 생성 모듈."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import TypedDict

SCHEMA_VERSION = "0.2.0"

# 프로파일러 에이전트와 공유하는 8각 인지 차트 축 (0~100: 높을수록 해당 성향이 강함)
COGNITIVE_BIAS_AXES: tuple[tuple[str, str], ...] = (
    ("intellectual_curiosity", "지적 호기심"),
    ("self_improvement", "자기계발"),
    ("social_awareness", "사회·시선"),
    ("depth_immersion", "깊이·몰입"),
    ("practical_orientation", "실용 지향"),
    ("emotional_comfort", "정서·위로"),
    ("creative_expression", "창의·표현"),
    ("entertainment_release", "오락·해방"),
)

# 시드 기반 현실적 분포를 위한 축별 기본 구간 (min, max)
_AXIS_BASELINE_RANGES: dict[str, tuple[float, float]] = {
    "intellectual_curiosity": (42.0, 58.0),
    "self_improvement": (50.0, 68.0),
    "social_awareness": (38.0, 55.0),
    "depth_immersion": (44.0, 62.0),
    "practical_orientation": (48.0, 66.0),
    "emotional_comfort": (46.0, 64.0),
    "creative_expression": (40.0, 58.0),
    "entertainment_release": (55.0, 78.0),
}

_INTERNAL_KEYWORD_POOL: tuple[str, ...] = (
    "AI 에이전트",
    "필터 버블",
    "숏폼 다이어트",
    "미니멀 라이프",
    "K-드라마 리뷰",
    "재테크 입문",
    "홈트 루틴",
    "비건 레시피",
    "인디 게임",
    "생산성 앱",
    "뉴스 큐레이션",
    "테크 유튜버",
    "명상 앱",
    "여행 브이로그",
    "주식 초보",
)

_EXTERNAL_KEYWORD_POOL: tuple[str, ...] = (
    "ChatGPT",
    "올림픽 하이라이트",
    "전세 사기 예방",
    "아이돌 컴백",
    "장마 대비",
    "비트코인 급등",
    "넷플릭스 신작",
    "총선 여론",
    "MZ 재테크",
    "AI 스타트업",
    "K-팝 월드투어",
    "기후 변화 뉴스",
    "e스포츠 결승",
    "반려동물 용품",
    "명품 리셀",
)

_YOUTUBE_CATEGORIES: tuple[str, ...] = (
    "뉴스/정치",
    "엔터테인먼트",
    "과학/기술",
    "게임",
    "음악",
    "스포츠",
    "교육",
    "라이프스타일",
)


class KeywordStat(TypedDict):
    keyword: str
    frequency: int
    trend_delta_pct: float


class ProfileAxisScore(TypedDict):
    key: str
    label: str
    avg_score: float


class CognitiveProfileMap(TypedDict):
    axes: list[ProfileAxisScore]
    cohort_size: int
    measurement_period: str


class InternalUserStats(TypedDict):
    top_keywords: list[KeywordStat]
    cognitive_bias_map: CognitiveProfileMap


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


class ExternalMarketTrends(TypedDict):
    google_trends: list[GoogleTrendItem]
    youtube_trending: list[YouTubeTrendItem]
    data_collected_at: str


class MockIntegratedData(TypedDict):
    schema_version: str
    generated_at: str
    internal_user_stats: InternalUserStats
    external_market_trends: ExternalMarketTrends


def _build_top_keywords(rng: random.Random, count: int = 10) -> list[KeywordStat]:
    pool_size = len(_INTERNAL_KEYWORD_POOL)
    keywords = rng.sample(_INTERNAL_KEYWORD_POOL, k=min(count, pool_size))
    return [
        {
            "keyword": keyword,
            "frequency": rng.randint(1_200, 18_500),
            "trend_delta_pct": round(rng.uniform(-12.0, 28.0), 1),
        }
        for keyword in keywords
    ]


def _build_profile_axis_scores(rng: random.Random) -> list[ProfileAxisScore]:
    """8각 성향 축별 현실적 평균 점수를 생성한다.

    코호트 내 1~2개 우세 성향 축을 두고, 나머지는 중간·저점 분포로
    편향되지 않은 랜덤이 아닌 통계적 분포를 모사한다.
    """
    axis_keys = [key for key, _ in COGNITIVE_BIAS_AXES]
    dominant_keys = set(rng.sample(axis_keys, k=rng.randint(1, 2)))
    suppressed_keys = set(rng.sample(axis_keys, k=rng.randint(1, 2)))

    scores: list[ProfileAxisScore] = []
    for key, label in COGNITIVE_BIAS_AXES:
        baseline_min, baseline_max = _AXIS_BASELINE_RANGES[key]

        if key in dominant_keys:
            avg_score = rng.uniform(baseline_max, min(baseline_max + 18.0, 92.0))
        elif key in suppressed_keys:
            avg_score = rng.uniform(max(baseline_min - 16.0, 18.0), baseline_min)
        else:
            avg_score = rng.uniform(baseline_min, baseline_max)

        scores.append(
            {
                "key": key,
                "label": label,
                "avg_score": round(avg_score, 1),
            }
        )

    return scores


def _build_cognitive_bias_map(rng: random.Random) -> CognitiveProfileMap:
    now = datetime.now(tz=UTC)
    period_start = now.replace(day=1).strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")

    return {
        "axes": _build_profile_axis_scores(rng),
        "cohort_size": rng.randint(8_500, 24_000),
        "measurement_period": f"{period_start} ~ {period_end}",
    }


def _build_google_trends(rng: random.Random, count: int = 8) -> list[GoogleTrendItem]:
    keywords = rng.sample(
        _EXTERNAL_KEYWORD_POOL, k=min(count, len(_EXTERNAL_KEYWORD_POOL))
    )
    return [
        {
            "keyword": keyword,
            "rank": index,
            "interest_index": rng.randint(55, 100),
            "wow_change_pct": round(rng.uniform(-8.0, 45.0), 1),
        }
        for index, keyword in enumerate(keywords, start=1)
    ]


def _build_youtube_trending(
    rng: random.Random, count: int = 8
) -> list[YouTubeTrendItem]:
    keywords = rng.sample(
        _EXTERNAL_KEYWORD_POOL, k=min(count, len(_EXTERNAL_KEYWORD_POOL))
    )
    return [
        {
            "keyword": keyword,
            "rank": index,
            "category": rng.choice(_YOUTUBE_CATEGORIES),
            "estimated_views": rng.randint(250_000, 8_500_000),
        }
        for index, keyword in enumerate(keywords, start=1)
    ]


def generate_mock_integrated_data(*, seed: int | None = None) -> MockIntegratedData:
    """비식별 내부 유저 통계와 외부 시장 트렌드를 통합한 가상 JSON 객체를 반환한다."""
    rng = random.Random(seed)
    generated_at = datetime.now(tz=UTC).isoformat()

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "internal_user_stats": {
            "top_keywords": _build_top_keywords(rng),
            "cognitive_bias_map": _build_cognitive_bias_map(rng),
        },
        "external_market_trends": {
            "google_trends": _build_google_trends(rng),
            "youtube_trending": _build_youtube_trending(rng),
            "data_collected_at": generated_at,
        },
    }
