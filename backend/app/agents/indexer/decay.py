import math
from datetime import datetime, timezone


def compute_weight(watched_at: datetime | None, lam: float = 0.001) -> float:
    """시청일 기준 지수 감쇠 가중치 계산.

    w = exp(-λ * days_since_watched)
    λ=0.001 기준: 100일→0.905, 1년→0.694, 3년→0.335
    """
    if watched_at is None:
        return 0.5

    now = datetime.now(timezone.utc)
    if watched_at.tzinfo is None:
        watched_at = watched_at.replace(tzinfo=timezone.utc)

    days = (now - watched_at).total_seconds() / 86400
    days = max(0.0, days)
    return math.exp(-lam * days)


def apply_decay_to_score(score: float, watched_at: datetime | None) -> float:
    """코사인 유사도 점수에 시간 감쇠 가중치 적용."""
    return score * compute_weight(watched_at)
