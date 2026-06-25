"""Navigator 프롬프트 빌더 + 공용 렌더 헬퍼."""

from __future__ import annotations

from app.agents.navigator.constants import (
    BEHAVIOR_AXES,
    VALUES_TEMPERAMENT_AXES,
)
from app.agents.profiler.axis_labels import SCORE_LABELS_KO


def render_scores(scores: dict[str, float], keys: tuple[str, ...]) -> str:
    """축 점수를 `- 라벨(key): 값` 줄 목록으로 렌더한다."""
    lines = []
    for key in keys:
        if key not in scores:
            continue
        label = SCORE_LABELS_KO.get(key, key)
        lines.append(f"- {label}({key}): {round(float(scores[key]), 1)}")
    return "\n".join(lines)


def render_profile_21(profile_21: dict[str, float]) -> str:
    """21축 전체를 렌더한다 (가치관·기질 13 + 행동 8)."""
    all_keys = tuple(SCORE_LABELS_KO.keys())
    return render_scores(profile_21, all_keys)


def render_8axis(scores: dict[str, float]) -> str:
    """행동 8축만 렌더한다."""
    return render_scores(scores, BEHAVIOR_AXES)


def render_13axis(scores: dict[str, float]) -> str:
    """가치관 10축 + 기질 3축만 렌더한다 (이상향 설계 축)."""
    return render_scores(scores, VALUES_TEMPERAMENT_AXES)


def render_interests(top_interests: dict[str, list] | None) -> str:
    if not top_interests:
        return "(관심사 데이터 없음)"
    parts = []
    channels = top_interests.get("channels") or []
    if channels:
        names = ", ".join(str(c.get("channel", "")) for c in channels[:5])
        parts.append(f"자주 본 채널: {names}")
    categories = top_interests.get("categories") or []
    if categories:
        ids = ", ".join(str(c.get("category_id", "")) for c in categories[:5])
        parts.append(f"상위 카테고리 ID: {ids}")
    return "\n".join(parts) if parts else "(관심사 데이터 없음)"
