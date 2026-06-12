"""Aggregator 파이프라인용 비식별 내부 사용자 통계 Mock 생성 모듈."""

from __future__ import annotations

import random
from datetime import UTC, datetime

from app.agents.aggregator.base import (
    CognitiveProfileMap,
    InternalUserStats,
    KeywordStat,
    ProfileAxisScore,
)

# 프로파일러 에이전트와 공유하는 8각 인지 차트 축 (0~100: 높을수록 해당 성향이 강함)
# TODO: profiler/base/axes.py SSOT로 통합 예정
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


def generate_internal_user_stats(*, seed: int | None = None) -> InternalUserStats:
    """비식별 내부 사용자 통계 Mock 데이터를 반환한다."""
    rng = random.Random(seed)

    return {
        "top_keywords": _build_top_keywords(rng),
        "cognitive_bias_map": _build_cognitive_bias_map(rng),
    }
