"""시청 catalog 통계 → 습관 지표 (프로파일·비교 공용)."""

from __future__ import annotations

from typing import Any


def habit_metrics_from_catalog_stats(
    stats: dict[str, Any] | None,
) -> dict[str, float]:
    """채널/카테고리 편중·다양성·탐색깊이 (0~1)."""
    if not stats:
        return _empty_habits()

    view_total = int(stats.get("total") or 0)
    if view_total <= 0:
        return _empty_habits()

    # 집중도/비율은 시청량 가중 분모, 탐색깊이는 영상 건수 분모
    weighted_total = float(stats.get("weighted_total") or view_total) or 1.0

    top5 = stats.get("channel_top5") or []
    top_channel = float(top5[0]["count"]) if top5 else 0.0
    channel_concentration = min(1.0, top_channel / weighted_total)

    cat_stats: dict[str, float] = stats.get("category_stats") or {}
    top_category = max(cat_stats.values()) if cat_stats else 0
    category_concentration = min(1.0, top_category / weighted_total)

    unique_channels = int(stats.get("unique_channels") or 1)
    exploration_depth = min(1.0, unique_channels / view_total * 3)

    n_categories = len(cat_stats)
    category_diversity = min(100.0, 20.0 + n_categories * 6.0) / 100.0

    return {
        "channel_concentration": round(channel_concentration, 3),
        "category_concentration": round(category_concentration, 3),
        "category_diversity": round(category_diversity, 3),
        "exploration_depth": round(exploration_depth, 3),
    }


def _empty_habits() -> dict[str, float]:
    return {
        "channel_concentration": 0.0,
        "category_concentration": 0.0,
        "category_diversity": 0.0,
        "exploration_depth": 0.0,
    }
