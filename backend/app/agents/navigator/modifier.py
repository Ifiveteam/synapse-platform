"""
Navigator — 이상향 수정 3모드

Mode 1. DIRECT  유저가 직접 축 수치 변경         (모델 없음)
Mode 2. CHAT    자연어 대화로 조금씩 조율          (gpt-4o-mini)
Mode 3. AUTO    LLM이 프로필 종합 분석 → 최적 설계  (gpt-4o)
"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .schemas import (
    AXIS_META,
    AxisKey,
    IdealRadarChart,
    IdealType,
    ProfilerLayerB,
    RadarChart,
)
from .tool import AXIS_VECTORS, _clamp, _build_ideal


# ──────────────────────────────────────────
# 내부 구조화 출력 스키마 (LLM → Python)
# ──────────────────────────────────────────


class AxisAdjustment(BaseModel):
    axis:   str   = Field(description="수정할 축 key (예: creative_expression)")
    delta:  float = Field(description="변화량 (양수=증가, 음수=감소). 절댓값 40 이하")


class ChatAdjustmentResult(BaseModel):
    """gpt-4o-mini 구조화 출력 — CHAT 모드"""
    adjustments: list[AxisAdjustment] = Field(description="적용할 축 변경 목록")
    reasoning:   str                  = Field(description="조정 이유 (한 줄)")
    reply:       str                  = Field(description="유저에게 보낼 응답 메시지")


class AutoIdealResult(BaseModel):
    """gpt-4o 구조화 출력 — AUTO 모드"""
    intellectual_curiosity: float = Field(ge=0, le=100)
    self_improvement:       float = Field(ge=0, le=100)
    social_awareness:       float = Field(ge=0, le=100)
    depth_immersion:        float = Field(ge=0, le=100)
    practical_orientation:  float = Field(ge=0, le=100)
    emotional_comfort:      float = Field(ge=0, le=100)
    creative_expression:    float = Field(ge=0, le=100)
    entertainment_release:  float = Field(ge=0, le=100)
    summary:   str = Field(description="이상향 한 줄 요약")
    reasoning: str = Field(description="설계 근거 (2~3줄)")


# ──────────────────────────────────────────
# Mode 1 — DIRECT
# ──────────────────────────────────────────


def modify_direct(
    ideal:     IdealRadarChart,
    axis:      str,
    new_value: float,
) -> tuple[IdealRadarChart, list[str]]:
    """
    특정 축 값을 직접 수정.
    AXIS_VECTORS 기반으로 연관 축 제안 메시지 반환.

    Returns:
        (updated_ideal, suggestions)  — suggestions는 UI 제안용 메시지 리스트
    """
    try:
        axis_key = AxisKey(axis)
    except ValueError:
        raise ValueError(f"알 수 없는 축: {axis}")

    clamped = _clamp(new_value)
    scores  = ideal.to_dict()
    scores[axis_key] = clamped

    updated = _build_ideal(
        ideal.user_id, ideal.ideal_type, scores,
        ideal.summary, ideal.direction or "", ideal.alpha or 0.55,
    )

    # 연관 축 제안 (AXIS_VECTORS 기반, 모델 없이)
    suggestions: list[str] = []
    vectors = AXIS_VECTORS.get(axis_key, {})
    # 현재 ideal_type 방향에서 연관 축 확인
    direction = "expansion" if ideal.ideal_type == IdealType.EXPANSION else "opposite"
    related   = vectors.get(direction, {})
    for related_key, delta_sign in related.items():
        if related_key == axis_key:
            continue
        related_name = AXIS_META[related_key]["name"]
        direction_str = "함께 올리는" if delta_sign > 0 else "함께 낮추는"
        suggestions.append(
            f"'{AXIS_META[axis_key]['name']}'을 바꾸면 '{related_name}'도 {direction_str} 걸 추천해요."
        )

    return updated, suggestions


# ──────────────────────────────────────────
# Mode 2 — CHAT (gpt-4o-mini)
# ──────────────────────────────────────────


_AXIS_NAMES_KR = "\n".join(
    f"  {key.value}: {meta['name']}"
    for key, meta in AXIS_META.items()
)

_CHAT_SYSTEM = f"""당신은 Navigator 에이전트입니다. 유저와 대화하며 이상향 8각 차트를 조율합니다.

축 목록 (key: 한글명):
{_AXIS_NAMES_KR}

규칙:
- 유저 메시지에서 수정 의도를 파악해 adjustments 목록으로 반환하세요.
- delta는 -40 ~ +40 범위. 작은 변화(±5~15)를 권장합니다.
- 유저가 방향을 말하지 않으면 adjustments는 빈 배열로, reply에서 확인 질문을 하세요.
- reply는 자연스러운 한국어로, 1~2문장.
"""


def modify_by_chat(
    ideal:        IdealRadarChart,
    user_message: str,
    current_radar: Optional[RadarChart] = None,
    layer_b:       Optional[ProfilerLayerB] = None,
) -> tuple[IdealRadarChart, ChatAdjustmentResult]:
    """
    자연어 메시지 → gpt-4o-mini → delta 추출 → ideal 업데이트

    Returns:
        (updated_ideal, result)  — result.reply를 유저에게 보여주세요
    """
    llm = ChatOpenAI(
        model       = "gpt-4o-mini",
        temperature = 0.3,
        api_key     = os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(ChatAdjustmentResult)

    # 컨텍스트 구성
    current_str = ""
    if current_radar:
        current_str = "\n현재 프로필: " + ", ".join(
            f"{k.value}={v:.0f}" for k, v in current_radar.to_dict().items()
        )
    ideal_str = "현재 이상향: " + ", ".join(
        f"{k.value}={v:.0f}" for k, v in ideal.to_dict().items()
    )
    layer_b_str = ""
    if layer_b:
        layer_b_str = (
            f"\nLayer B: 주체성={layer_b.search_active_ratio:.2f}, "
            f"채널편중={layer_b.viewing_concentration:.2f}(↑나쁨), "
            f"취향다양성={layer_b.taste_diversity_index}, "
            f"탐색깊이={layer_b.exploration_depth:.2f}"
        )

    user_prompt = f"{ideal_str}{current_str}{layer_b_str}\n\n유저: {user_message}"

    result: ChatAdjustmentResult = llm.invoke([
        {"role": "system",  "content": _CHAT_SYSTEM},
        {"role": "user",    "content": user_prompt},
    ])

    # delta 적용
    scores = ideal.to_dict()
    for adj in result.adjustments:
        try:
            key = AxisKey(adj.axis)
            scores[key] = _clamp(scores[key] + adj.delta)
        except ValueError:
            pass

    updated = _build_ideal(
        ideal.user_id, ideal.ideal_type, scores,
        ideal.summary, ideal.direction or "", ideal.alpha or 0.55,
    )

    return updated, result


# ──────────────────────────────────────────
# Mode 3 — AUTO OPTIMAL (gpt-4o)
# ──────────────────────────────────────────


_AUTO_SYSTEM = """당신은 개인 미디어 소비 패턴 전문가입니다.
유저의 현재 프로필(Layer A 8각 + Layer B 4지표)을 분석하여
가장 이상적인 이상향 8각 차트를 설계해주세요.

설계 기준:
1. 현재 dominant 축(높은 축)은 적절히 낮추거나 유지
2. weak 축(낮은 축)은 자연스럽게 높이기
3. Layer B 주체성(search_active_ratio)이 낮으면 → 다양성 방향 강화
4. Layer B 채널편중도(viewing_concentration)가 높으면 (나쁨) → 분산 유도
5. 유저 목표가 있으면 최우선 반영
6. 모든 축 값은 0~100 범위

수치를 너무 극단적으로 설정하지 마세요 (최대 변화폭: 현재 대비 ±40).
"""


def optimize_auto(
    current_radar:  RadarChart,
    layer_b:        ProfilerLayerB,
    top5_interests: list[str],
    user_goal:      Optional[str] = None,
) -> IdealRadarChart:
    """
    gpt-4o가 Layer A + Layer B + 목표를 종합 분석하여 최적 이상향 설계.

    Args:
        user_goal: 유저가 입력한 목표 텍스트 (선택)
    Returns:
        AI가 설계한 IdealRadarChart (ideal_type=custom)
    """
    llm = ChatOpenAI(
        model       = "gpt-4o",
        temperature = 0.5,
        api_key     = os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(AutoIdealResult)

    current_str = "\n".join(
        f"  {k.value} ({AXIS_META[k]['name']}): {v:.0f}"
        for k, v in current_radar.to_dict().items()
    )
    layer_b_str = (
        f"  주체성(search_active_ratio): {layer_b.search_active_ratio:.2f}  ← 높을수록 좋음\n"
        f"  채널편중도(viewing_concentration): {layer_b.viewing_concentration:.2f}  ← 높을수록 나쁨\n"
        f"  취향다양성(taste_diversity_index): {layer_b.taste_diversity_index}\n"
        f"  탐색깊이(exploration_depth): {layer_b.exploration_depth:.2f}"
    )
    interests_str = ", ".join(top5_interests) if top5_interests else "미지정"
    goal_str      = f"\n유저 목표: {user_goal}" if user_goal else ""

    user_prompt = (
        f"【현재 프로필 Layer A】\n{current_str}\n\n"
        f"【Layer B 인지주권 지표】\n{layer_b_str}\n\n"
        f"【TOP5 관심사】 {interests_str}"
        f"{goal_str}\n\n"
        f"위 데이터를 바탕으로 최적의 이상향 8각 차트를 설계해주세요."
    )

    result: AutoIdealResult = llm.invoke([
        {"role": "system", "content": _AUTO_SYSTEM},
        {"role": "user",   "content": user_prompt},
    ])

    scores = {
        AxisKey.INTELLECTUAL_CURIOSITY: _clamp(result.intellectual_curiosity),
        AxisKey.SELF_IMPROVEMENT:       _clamp(result.self_improvement),
        AxisKey.SOCIAL_AWARENESS:       _clamp(result.social_awareness),
        AxisKey.DEPTH_IMMERSION:        _clamp(result.depth_immersion),
        AxisKey.PRACTICAL_ORIENTATION:  _clamp(result.practical_orientation),
        AxisKey.EMOTIONAL_COMFORT:      _clamp(result.emotional_comfort),
        AxisKey.CREATIVE_EXPRESSION:    _clamp(result.creative_expression),
        AxisKey.ENTERTAINMENT_RELEASE:  _clamp(result.entertainment_release),
    }

    ideal = _build_ideal(
        current_radar.user_id,
        IdealType.CUSTOM,
        scores,
        summary   = result.summary,
        direction = "AUTO_OPTIMAL",
        alpha     = 1.0,
    )
    # reasoning은 별도 필드에 저장 (direction 필드 오용 방지)
    ideal = ideal.model_copy(update={"reasoning": result.reasoning})
    return ideal
