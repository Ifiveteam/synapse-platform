"""user_profile_history 점수 필드 — 순환 import 방지용 공용 모듈."""

from __future__ import annotations

SCORE_FIELDS = (
    "self_direction",
    "stimulation",
    "achievement",
    "power",
    "security",
    "benevolence",
    "universalism",
    "hedonism",
    "conformity",
    "tradition",
    "novelty_seeking",
    "persistence",
    "self_transcendence",
    "exploration",
    "analytical",
    "creativity",
    "execution",
    "achievement_drive",
    "autonomy",
    "sociality",
    "sensitivity",
)


def history_scores_dict(history) -> dict[str, float]:
    return {
        key: float(getattr(history, key) or 0.0)
        for key in SCORE_FIELDS
        if getattr(history, key) is not None
    }
