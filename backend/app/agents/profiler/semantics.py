"""영상 의미라벨(tone/intent/value) → 13축 근거 매핑.

고정 어휘는 schemas/profiler/llm/video.py(스키마 제약)가 SSOT.
여기선 그 라벨을 13축(가치관·기질) 근거 강도로 환산한다 (build_profile이 사용).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.schemas.profiler.llm.video import INTENTS, TONES, VALUES

_VT_AXES: tuple[str, ...] = (
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
)

# 라벨 → {축: 가중(-1~1)}. 음수는 해당 축 근거를 깎는다(0 하한).
LABEL_AXIS_MAP: dict[str, dict[str, float]] = {
    # ── tones ──
    "차분한": {"security": 0.5, "persistence": 0.4, "stimulation": -0.3},
    "활기찬": {"stimulation": 0.6, "hedonism": 0.4},
    "진지한": {"persistence": 0.5, "achievement": 0.4},
    "유머러스": {"hedonism": 0.6, "stimulation": 0.3},
    "따뜻한": {"benevolence": 0.6, "self_transcendence": 0.4},
    "자극적": {"stimulation": 0.7, "novelty_seeking": 0.4},
    "비판적": {"universalism": 0.5, "self_direction": 0.4},
    "감성적": {"self_transcendence": 0.5, "hedonism": 0.3},
    "정보적": {"achievement": 0.4, "universalism": 0.4},
    "영감적": {"self_direction": 0.5, "self_transcendence": 0.4, "achievement": 0.3},
    # ── intents ──
    "정보전달": {"universalism": 0.5, "achievement": 0.4},
    "학습": {"achievement": 0.6, "persistence": 0.5},
    "오락": {"hedonism": 0.6, "stimulation": 0.4},
    "동기부여": {"achievement": 0.5, "self_direction": 0.4},
    "공감": {"benevolence": 0.6, "self_transcendence": 0.4},
    "설득": {"power": 0.5, "achievement": 0.3},
    "영감": {"self_direction": 0.5, "self_transcendence": 0.4},
    "휴식": {"security": 0.5, "hedonism": 0.4, "stimulation": -0.2},
    "토론": {"universalism": 0.5, "self_direction": 0.4},
    "트렌드": {"novelty_seeking": 0.5, "stimulation": 0.4, "conformity": 0.3},
    # ── values ──
    "성장": {"achievement": 0.6, "persistence": 0.5},
    "효율": {"achievement": 0.5, "power": 0.3},
    "자유": {"self_direction": 0.6, "novelty_seeking": 0.4},
    "공동체": {"benevolence": 0.5, "conformity": 0.4},
    "안정": {"security": 0.6, "tradition": 0.4},
    "도전": {"novelty_seeking": 0.5, "stimulation": 0.4, "achievement": 0.3},
    "심미": {"hedonism": 0.5, "self_direction": 0.4},
    "정의": {"universalism": 0.6, "self_transcendence": 0.4},
    "전통": {"tradition": 0.7, "conformity": 0.4},
    "자기표현": {"self_direction": 0.6, "hedonism": 0.3},
}

# 누락 라벨 점검용 (어휘 전체가 매핑돼 있는지 — import 시 보장)
_ALL_LABELS = set(TONES) | set(INTENTS) | set(VALUES)
assert _ALL_LABELS <= set(LABEL_AXIS_MAP), (
    f"매핑 누락 라벨: {_ALL_LABELS - set(LABEL_AXIS_MAP)}"
)


def compute_semantic_evidence(
    label_weights: Mapping[str, float],
) -> dict[str, float]:
    """집계된 라벨 가중치 → 13축 근거 강도(0~1).

    label_weights: {라벨: 가중합}  (watch_count·빈도 반영된 누적치)
    """
    total = sum(w for w in label_weights.values() if w > 0)
    if total <= 0:
        return dict.fromkeys(_VT_AXES, 0.0)
    raw = dict.fromkeys(_VT_AXES, 0.0)
    for label, weight in label_weights.items():
        for axis, coef in LABEL_AXIS_MAP.get(label, {}).items():
            raw[axis] += weight * coef
    return {axis: max(0.0, min(1.0, raw[axis] / total)) for axis in _VT_AXES}
