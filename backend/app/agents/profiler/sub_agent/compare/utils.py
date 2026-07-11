"""비교 서브 에이전트 — 결정론적 diff."""

from __future__ import annotations

from typing import Any

from app.agents.profiler.habit_metrics import habit_metrics_from_catalog_stats
from app.models.user_profile_history import UserProfileHistory
from app.services.profiler.scores import SCORE_FIELDS, history_scores_dict


def _normalize_traits(raw: list | dict | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [str(v) for v in raw.values() if v]
    return [str(t) for t in raw if t]


def _catalog_stats(row: UserProfileHistory) -> dict[str, Any]:
    evidence = row.supporting_evidence or {}
    if isinstance(evidence, dict):
        stats = evidence.get("catalog_stats")
        if isinstance(stats, dict):
            return stats
    return {}


def _top_channel_names(stats: dict[str, Any], limit: int = 5) -> list[str]:
    names: list[str] = []
    for item in stats.get("channel_top5") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("channel") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def _portrait_dict(row: UserProfileHistory) -> dict[str, Any]:
    p = row.portrait or {}
    return p if isinstance(p, dict) else {}


def _axis_value_map(items: Any) -> dict[str, float]:
    """portrait의 disposition/interest([{axis, value}, ...]) → {axis: value}."""
    out: dict[str, float] = {}
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                axis = str(it.get("axis") or "").strip()
                if axis:
                    out[axis] = float(it.get("value") or 0.0)
    return out


def _top_channels(stats: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    """상위 채널 목록(채널명 + 시청 수) — 화면 '상위 채널'과 동일 소스."""
    out: list[dict[str, Any]] = []
    for item in stats.get("channel_top5") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("channel") or "").strip()
        if not name:
            continue
        out.append({"channel": name, "count": int(item.get("count") or 0)})
        if len(out) >= limit:
            break
    return out


def _snapshot_summary(row: UserProfileHistory) -> dict[str, Any]:
    stats = _catalog_stats(row)
    return {
        "snapshot_id": str(row.id),
        "snapshot_date": row.snapshot_date,
        "persona_label": (row.portrait or {}).get("persona_label"),
        "summary_text": row.summary_text or "",
        "scores": history_scores_dict(row),
        "habits": habit_metrics_from_catalog_stats(stats),
        "shorts_ratio": float(stats.get("shorts_ratio") or 0.0),
        "total_videos": int(stats.get("total") or 0),
    }


def compare_profile_snapshots(
    from_row: UserProfileHistory,
    to_row: UserProfileHistory,
) -> dict[str, Any]:
    from_scores = history_scores_dict(from_row)
    to_scores = history_scores_dict(to_row)
    scores_delta = {
        key: round(to_scores.get(key, 0.0) - from_scores.get(key, 0.0), 1)
        for key in SCORE_FIELDS
    }

    from_stats = _catalog_stats(from_row)
    to_stats = _catalog_stats(to_row)
    habits_from = habit_metrics_from_catalog_stats(from_stats)
    habits_to = habit_metrics_from_catalog_stats(to_stats)
    habits_delta = {
        key: round(habits_to[key] - habits_from[key], 3) for key in habits_from
    }

    from_traits = set(_normalize_traits(from_row.dominant_traits))
    to_traits = set(_normalize_traits(to_row.dominant_traits))

    from_channels = set(_top_channel_names(from_stats))
    to_channels = set(_top_channel_names(to_stats))

    shorts_delta = round(
        float(to_stats.get("shorts_ratio") or 0.0)
        - float(from_stats.get("shorts_ratio") or 0.0),
        3,
    )

    # 화면(비교 페이지)에서 주로 보여주는 축들 — 성향 6축·관심 도메인·상위 채널.
    # HTTP 응답 스키마엔 없는 필드지만, narrative LLM이 화면과 같은 근거로
    # 요약하도록 diff에 함께 실어 보낸다(응답 검증 시엔 무시됨).
    from_disp = _axis_value_map(_portrait_dict(from_row).get("disposition"))
    to_disp = _axis_value_map(_portrait_dict(to_row).get("disposition"))
    disposition_delta = {
        key: round(to_disp.get(key, 0.0) - from_disp.get(key, 0.0), 1)
        for key in dict.fromkeys([*from_disp, *to_disp])
    }

    from_interest = _axis_value_map(_portrait_dict(from_row).get("interest"))
    to_interest = _axis_value_map(_portrait_dict(to_row).get("interest"))
    interest_delta = {
        key: round(to_interest.get(key, 0.0) - from_interest.get(key, 0.0), 1)
        for key in dict.fromkeys([*from_interest, *to_interest])
    }

    return {
        "from_snapshot": _snapshot_summary(from_row),
        "to_snapshot": _snapshot_summary(to_row),
        "scores_delta": scores_delta,
        "habits_from": habits_from,
        "habits_to": habits_to,
        "habits_delta": habits_delta,
        "shorts_ratio_delta": shorts_delta,
        "traits_added": sorted(to_traits - from_traits),
        "traits_removed": sorted(from_traits - to_traits),
        "channels_added": sorted(to_channels - from_channels),
        "channels_removed": sorted(from_channels - to_channels),
        # ── 화면 중심 축 (narrative 근거용, 응답에선 무시) ──
        "disposition_from": from_disp,
        "disposition_to": to_disp,
        "disposition_delta": disposition_delta,
        "interest_from": from_interest,
        "interest_to": to_interest,
        "interest_delta": interest_delta,
        "from_top_channels": _top_channels(from_stats),
        "to_top_channels": _top_channels(to_stats),
    }
