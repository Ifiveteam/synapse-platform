"""축 점수 → 페르소나 라벨 (결정적 규칙). profiler(현재)·navigator(이상향) 공유.

명사   = 행동 8축 최고점(argmax)
형용사 = 가치관 10축 중 "자기 평균에서 가장 벗어난" 축 + 부호(50 기준 높/낮)
         · 명사(행동)의 주재료 가치축은 제외 → 동어반복 완화
         · 가치 점수가 평탄(spread<MIN)하면 "균형 잡힌"
동점은 기질 친화 → 절대편차 → 고정순서 순으로 깬다.
"""

from __future__ import annotations

from collections.abc import Mapping

NOUN_BY_BEHAVIOR: dict[str, str] = {
    "exploration": "탐험가",
    "analytical": "분석가",
    "creativity": "창작가",
    "execution": "실행가",
    "achievement_drive": "성취가",
    "autonomy": "소신가",
    "sociality": "소통가",
    "sensitivity": "감성가",
}

# (높음어, 낮음어)
ADJ_BY_VALUE: dict[str, tuple[str, str]] = {
    "self_direction": ("자기주도적인", "순응적인"),
    "stimulation": ("모험적인", "차분한"),
    "achievement": ("성취지향적인", "여유로운"),
    "power": ("야심찬", "겸손한"),
    "security": ("신중한", "대담한"),
    "benevolence": ("따뜻한", "담백한"),
    "universalism": ("포용적인", "실리적인"),
    "hedonism": ("유쾌한", "절제된"),
    "conformity": ("조화로운", "자유분방한"),
    "tradition": ("전통적인", "진보적인"),
}

# 행동축 ← 주재료 가치축 (동어반복 완화 — behavior_map 가중 상위 가치축)
_BEHAVIOR_VALUE_SOURCES: dict[str, tuple[str, ...]] = {
    "exploration": ("self_direction", "stimulation"),
    "analytical": ("achievement", "universalism"),
    "creativity": ("self_direction", "stimulation", "hedonism"),
    "execution": ("achievement",),
    "achievement_drive": ("achievement", "power"),
    "autonomy": ("self_direction", "conformity"),
    "sociality": ("benevolence", "universalism", "hedonism"),
    "sensitivity": ("hedonism", "stimulation"),
}

# 기질 → 친화 가치축 (동점 tie-break, 이름엔 안 들어가는 기질의 역할)
_TEMPERAMENT_AFFINITY: dict[str, frozenset[str]] = {
    "novelty_seeking": frozenset({"self_direction", "stimulation"}),
    "persistence": frozenset({"achievement", "security", "conformity"}),
    "self_transcendence": frozenset({"universalism", "benevolence"}),
}

_VALUE_ORDER: tuple[str, ...] = tuple(ADJ_BY_VALUE)
_BEHAVIOR_ORDER: tuple[str, ...] = tuple(NOUN_BY_BEHAVIOR)
_TEMPERAMENT_AXES: tuple[str, ...] = tuple(_TEMPERAMENT_AFFINITY)
_MID = 50.0
_MIN_TRAIT = 9.0  # |점수-50| 이 미만이면 "특징"으로 안 봄(중립). 다 미만이면 균형


def _dominant_behavior(behavior8: Mapping[str, float]) -> str:
    return max(
        _BEHAVIOR_ORDER,
        key=lambda a: (float(behavior8.get(a, 0.0)), -_BEHAVIOR_ORDER.index(a)),
    )


def persona_from_scores(
    values13: Mapping[str, float], behavior8: Mapping[str, float]
) -> str:
    """현재/이상향 축 → '형용사 명사' 페르소나 (결정적)."""
    noun_axis = _dominant_behavior(behavior8)
    noun = NOUN_BY_BEHAVIOR[noun_axis]

    vals = {k: float(values13.get(k, _MID)) for k in _VALUE_ORDER}
    dom_temp = max(_TEMPERAMENT_AXES, key=lambda a: float(values13.get(a, _MID)))
    affinity = _TEMPERAMENT_AFFINITY.get(dom_temp, frozenset())

    def _rank(axis: str) -> tuple[float, int, int]:
        return (
            abs(vals[axis] - _MID),  # 1) 절대 편차(특징 강도)
            1 if axis in affinity else 0,  # 2) 기질 친화 (동점)
            -_VALUE_ORDER.index(axis),  # 3) 고정 순서 (최종)
        )

    ranked = sorted(_VALUE_ORDER, key=_rank, reverse=True)
    strong = [k for k in ranked if abs(vals[k] - _MID) >= _MIN_TRAIT]
    if not strong:  # 두드러진 가치가 없음 → 진짜 평탄
        return f"균형 잡힌 {noun}"

    # 동어반복 완화: 명사 재료 가치축은 피하되, 대안이 없으면 그대로(정확 우선)
    excluded = set(_BEHAVIOR_VALUE_SOURCES.get(noun_axis, ()))
    non_source = [k for k in strong if k not in excluded]
    adj_axis = non_source[0] if non_source else strong[0]

    hi, lo = ADJ_BY_VALUE[adj_axis]
    word = hi if vals[adj_axis] > _MID else lo
    return f"{word} {noun}"
