"""네비게이터 자체 13축 → 8축 매핑 (프로파일러와 독립 소유).

LLM이 설계한 이상향 13축(가치관10+기질3)에서 행동 8축 타깃을 파생한다.
프로파일러의 rule_based_behavior_spider와 동일 수식으로 시작하지만, 의도가
다르므로(설계 타깃 vs 관찰 추론) 네비게이터가 독립적으로 소유·튜닝한다.
"""

from __future__ import annotations

from app.agents.navigator.constants import AXIS_MAX, AXIS_MIN


def _clamp(value: float) -> float:
    return max(AXIS_MIN, min(AXIS_MAX, float(value)))


def _blend(v: dict[str, float], *weighted: tuple[str, float]) -> float:
    """가중 평균 — (축키, 가중치) 쌍들의 가중합."""
    total = sum(w for _, w in weighted)
    if total <= 0:
        return 0.0
    return sum(float(v.get(key, 0.0)) * w for key, w in weighted) / total


def derive_8_from_13(values13: dict[str, float]) -> dict[str, float]:
    """이상향 가치관·기질 13축 → 행동 8축 타깃 (0~100)."""
    v = values13
    return {
        "exploration": round(
            _clamp(
                _blend(
                    v,
                    ("novelty_seeking", 0.55),
                    ("self_direction", 0.28),
                    ("stimulation", 0.17),
                )
            ),
            1,
        ),
        "analytical": round(
            _clamp(
                _blend(
                    v,
                    ("achievement", 0.32),
                    ("universalism", 0.33),
                    ("persistence", 0.25),
                )
            ),
            1,
        ),
        "creativity": round(
            _clamp(
                _blend(
                    v,
                    ("self_direction", 0.38),
                    ("stimulation", 0.34),
                    ("hedonism", 0.18),
                )
            ),
            1,
        ),
        "execution": round(
            _clamp(_blend(v, ("persistence", 0.52), ("achievement", 0.38))), 1
        ),
        "achievement_drive": round(
            _clamp(
                _blend(
                    v,
                    ("achievement", 0.52),
                    ("persistence", 0.33),
                    ("power", 0.15),
                )
            ),
            1,
        ),
        "autonomy": round(
            _clamp(
                float(v.get("self_direction", 0.0)) * 0.45
                + float(v.get("novelty_seeking", 0.0)) * 0.35
                + (100.0 - float(v.get("conformity", 0.0))) * 0.2
            ),
            1,
        ),
        "sociality": round(
            _clamp(
                _blend(
                    v,
                    ("benevolence", 0.42),
                    ("universalism", 0.28),
                    ("hedonism", 0.18),
                )
            ),
            1,
        ),
        "sensitivity": round(
            _clamp(
                _blend(
                    v,
                    ("self_transcendence", 0.38),
                    ("hedonism", 0.28),
                    ("stimulation", 0.22),
                )
            ),
            1,
        ),
    }
