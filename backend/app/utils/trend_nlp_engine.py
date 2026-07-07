"""에이전트 정제 키워드 기반 급상승 스코어링 엔진 (Phase 2-5 경량화).

명사 추출·정규식 파싱은 서브 에이전트 LLM에 위임하고,
이 모듈은 청정 키워드 세트에 대해 7일 이동평균 대비 급상승 점수만 산출한다.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

# 급상승 스코어 ZeroDivision 방어 상수
TREND_SCORE_EPSILON = 0.1
DEFAULT_TOP_N = 30


class TrendNLPEngine:
    """에이전트가 정제한 키워드 → 일별 빈도·급상승 랭킹 빌더."""

    def build_daily_counts(self, refined_keywords: Iterable[str]) -> dict[str, int]:
        """정제된 키워드 배열을 일별 빈도 dict로 집계."""
        counter = Counter(
            keyword.strip()
            for keyword in refined_keywords
            if keyword and str(keyword).strip()
        )
        return dict(counter)

    def build_ranking(
        self,
        today_counts: Mapping[str, int],
        historical_daily: Sequence[Mapping[str, int]],
        *,
        top_n: int = DEFAULT_TOP_N,
        epsilon: float = TREND_SCORE_EPSILON,
    ) -> dict[str, Any]:
        """7일 이력 대비 급상승 키워드 랭킹 JSONB 페이로드 생성."""
        return calculate_trending_keywords(
            today_counts,
            historical_daily,
            top_n=top_n,
            epsilon=epsilon,
        )


def calculate_trending_score(
    count_today: int,
    avg_count_7days: float,
    *,
    epsilon: float = TREND_SCORE_EPSILON,
) -> float:
    """급상승 가중치: (Count_today + ε) / (Avg_7d + ε) × ln(Count_today + 1)."""
    if count_today <= 0:
        return 0.0
    numerator = count_today + epsilon
    denominator = avg_count_7days + epsilon
    surge_ratio = numerator / denominator
    log_boost = math.log(count_today + 1)
    return round(surge_ratio * log_boost, 6)


def calculate_trending_keywords(
    today_counts: Mapping[str, int],
    historical_daily: Sequence[Mapping[str, int]],
    *,
    top_n: int = DEFAULT_TOP_N,
    epsilon: float = TREND_SCORE_EPSILON,
) -> dict[str, Any]:
    """오늘 빈도 vs 지난 7일 이동 평균 비교 → 급상승 키워드 랭킹 산출."""
    lookback_days = max(len(historical_daily), 1)

    all_historical_keys: set[str] = set()
    for day_counts in historical_daily:
        all_historical_keys.update(day_counts.keys())

    candidate_keys = set(today_counts.keys()) | all_historical_keys

    scored: list[dict[str, Any]] = []
    for keyword in candidate_keys:
        count_today = int(today_counts.get(keyword, 0))
        if count_today <= 0:
            continue

        total_past = sum(
            int(day_counts.get(keyword, 0)) for day_counts in historical_daily
        )
        avg_7day = total_past / lookback_days
        score = calculate_trending_score(
            count_today,
            avg_7day,
            epsilon=epsilon,
        )
        scored.append(
            {
                "keyword": keyword,
                "score": score,
                "count_today": count_today,
                "avg_7day": round(avg_7day, 4),
                "total_past_7day": total_past,
            }
        )

    scored.sort(key=lambda row: (-row["score"], -row["count_today"], row["keyword"]))
    ranking = [
        {**row, "rank": index} for index, row in enumerate(scored[:top_n], start=1)
    ]

    return {
        "algorithm": "surge_ratio_x_log_boost",
        "source": "agent_refined_keywords",
        "epsilon": epsilon,
        "lookback_days": lookback_days,
        "daily_counts": dict(today_counts),
        "ranking": ranking,
        "meta": {
            "unique_keywords_today": len(today_counts),
            "candidates_scored": len(scored),
            "top_n": top_n,
        },
    }
