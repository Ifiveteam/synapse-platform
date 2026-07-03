"""Navigator 프롬프트 빌더 + 공용 렌더 헬퍼."""

from __future__ import annotations

from app.agents.navigator.constants import (
    BEHAVIOR_AXES,
    DISPOSITION_AXES,
    DISPOSITION_LABELS_KO,
    INTEREST_DOMAINS,
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


def render_disposition(disposition: dict[str, float]) -> str:
    """성향 6축을 `- 라벨(key): 값` 목록으로 렌더한다."""
    if not disposition:
        return "(성향 데이터 없음)"
    lines = []
    for key in DISPOSITION_AXES:
        if key not in disposition:
            continue
        label = DISPOSITION_LABELS_KO.get(key, key)
        lines.append(f"- {label}({key}): {round(float(disposition[key]), 1)}")
    return "\n".join(lines) if lines else "(성향 데이터 없음)"


def render_domains(interest: dict[str, float]) -> str:
    """관심 도메인 분포를 `- 도메인: 값` 목록으로 렌더한다 (값 큰 순)."""
    if not interest:
        return "(관심 도메인 데이터 없음)"
    ordered = sorted(INTEREST_DOMAINS, key=lambda d: interest.get(d, 0.0), reverse=True)
    lines = [f"- {d}: {round(float(interest.get(d, 0.0)), 1)}" for d in ordered]
    return "\n".join(lines)


def render_portrait(
    *,
    disposition: dict[str, float],
    interest: dict[str, float],
    keywords: list[str] | None = None,
    persona_label: str = "",
) -> str:
    """portrait 신호(별칭·키워드·성향 6축·관심 도메인)를 한 블록으로 렌더한다."""
    parts = []
    if persona_label:
        parts.append(f"현재 별칭: {persona_label}")
    if keywords:
        parts.append(f"키워드: {', '.join(str(k) for k in keywords[:7])}")
    parts.append(f"[현재 성향 6축]\n{render_disposition(disposition)}")
    parts.append(f"[현재 관심 도메인]\n{render_domains(interest)}")
    return "\n".join(parts)


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
