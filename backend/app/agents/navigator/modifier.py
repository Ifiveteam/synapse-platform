"""
Navigator — 이상향 수정 3모드

Mode 1. DIRECT  유저가 직접 축 수치 변경         (모델 없음)
Mode 2. CHAT    자연어 대화로 조금씩 조율          (gpt-4o-mini)
Mode 3. AUTO    LLM이 프로필 종합 분석 → 최적 설계  (gpt-4o)

반대방향형: 페르소나 분류 → Gemini LLM → 반대 페르소나 → 8축 수치
"""

import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .schemas import (
    AXIS_META,
    AxisKey,
    Guide,
    IdealRadarChart,
    IdealType,
    ProfilerLayerB,
    RadarChart,
)
from .tool import AXIS_VECTORS, _build_ideal, _clamp

# ──────────────────────────────────────────
# 내부 구조화 출력 스키마 (LLM → Python)
# ──────────────────────────────────────────


class AxisAdjustment(BaseModel):
    axis: str = Field(description="수정할 축 key (예: creative_expression)")
    delta: float = Field(description="변화량 (양수=증가, 음수=감소). 절댓값 40 이하")


class ChatAdjustmentResult(BaseModel):
    """gpt-4o-mini 구조화 출력 — CHAT 모드"""

    adjustments: list[AxisAdjustment] = Field(description="적용할 축 변경 목록")
    reasoning: str = Field(description="조정 이유 (한 줄)")
    reply: str = Field(description="유저에게 보낼 응답 메시지")


class AutoIdealResult(BaseModel):
    """gpt-4o 구조화 출력 — AUTO 모드"""

    intellectual_curiosity: float = Field(ge=0, le=100)
    self_improvement: float = Field(ge=0, le=100)
    social_awareness: float = Field(ge=0, le=100)
    depth_immersion: float = Field(ge=0, le=100)
    practical_orientation: float = Field(ge=0, le=100)
    emotional_comfort: float = Field(ge=0, le=100)
    creative_expression: float = Field(ge=0, le=100)
    entertainment_release: float = Field(ge=0, le=100)
    summary: str = Field(description="이상향 한 줄 요약")
    reasoning: str = Field(description="설계 근거 (2~3줄)")


class OppositeIdealResult(BaseModel):
    """Gemini 구조화 출력 — 반대방향형 이상향 (페르소나 기반)"""

    intellectual_curiosity: float = Field(ge=0, le=100)
    self_improvement: float = Field(ge=0, le=100)
    social_awareness: float = Field(ge=0, le=100)
    depth_immersion: float = Field(ge=0, le=100)
    practical_orientation: float = Field(ge=0, le=100)
    emotional_comfort: float = Field(ge=0, le=100)
    creative_expression: float = Field(ge=0, le=100)
    entertainment_release: float = Field(ge=0, le=100)
    opposite_persona_name: str = Field(
        description="반대 페르소나 이름 (예: 무목적 탐험가)"
    )
    opposite_persona_desc: str = Field(description="반대 페르소나 설명 (1~2문장)")
    summary: str = Field(description="반대 이상향 한 줄 요약 (한국어)")
    reasoning: str = Field(description="왜 이 페르소나가 반대인지 설명 (2~3줄, 한국어)")
    guide_steps: list[str] = Field(
        description=(
            "이 반대 페르소나처럼 콘텐츠를 소비하기 위한 주차별 행동 가이드 4개. "
            "형식: '1주차 [축이름]: 구체적 행동'. 반드시 4개 반환."
        )
    )


# ──────────────────────────────────────────
# 반대방향형 이상향 — 페르소나 기반 LLM (Gemini)
# ──────────────────────────────────────────

# 페르소나 분류표 (수식 기반, 순서 중요 — 위에서부터 매칭)
_PERSONA_TABLE = [
    {
        "name": "실용적 성취자",
        "desc": (
            "목표 달성과 효율을 위해 콘텐츠를 소비하는 사람. "
            "실생활에 바로 쓸 수 있는 정보와 자기계발을 추구한다."
        ),
        "condition": lambda s: (
            s["practical_orientation"] >= 65 or s["self_improvement"] >= 65
        ),
    },
    {
        "name": "지적 탐험가",
        "desc": (
            "새로운 지식과 개념을 깊이 파고드는 사람. "
            "분석적이고 호기심 주도적인 소비 패턴을 가진다."
        ),
        "condition": lambda s: (
            s["intellectual_curiosity"] >= 65 or s["depth_immersion"] >= 65
        ),
    },
    {
        "name": "감성 창조자",
        "desc": (
            "감정·예술·창의적 표현에 몰입하는 사람. "
            "아름다움과 감동을 통해 자신을 표현하고 힐링한다."
        ),
        "condition": lambda s: (
            s["creative_expression"] >= 65 or s["emotional_comfort"] >= 65
        ),
    },
    {
        "name": "사회적 공감자",
        "desc": (
            "사회 이슈와 타인의 관점에 관심이 많은 사람. "
            "공감과 연대를 통해 콘텐츠를 소비한다."
        ),
        "condition": lambda s: s["social_awareness"] >= 65,
    },
    {
        "name": "가벼운 소비자",
        "desc": (
            "오락과 휴식을 위해 부담 없이 콘텐츠를 즐기는 사람. "
            "스트레스 해소와 즐거움이 주된 동기다."
        ),
        "condition": lambda s: (
            s["entertainment_release"] >= 65 and max(s.values()) < 75
        ),
    },
    {
        "name": "균형 추구자",
        "desc": (
            "특정 편향 없이 다양한 영역을 고르게 소비하는 사람. "
            "안정적이고 넓은 관심사를 가진다."
        ),
        "condition": lambda s: True,  # fallback
    },
]


def classify_persona(radar: RadarChart) -> dict:
    """
    8각 데이터 → 페르소나 분류 (수식 기반, LLM 불필요).
    Returns: {"name": str, "desc": str}
    """
    scores = {k.value: v for k, v in radar.to_dict().items()}
    for persona in _PERSONA_TABLE:
        if persona["condition"](scores):
            return {"name": persona["name"], "desc": persona["desc"]}
    return {"name": "균형 추구자", "desc": _PERSONA_TABLE[-1]["desc"]}


_OPPOSITE_SYSTEM = """당신은 개인 미디어 소비 패턴 전문가이자 철학적 사고를 갖춘 큐레이터입니다.

유저의 현재 콘텐츠 소비 페르소나를 보고, 그 정체성과 진정한 의미의 반대 페르소나를 도출한 뒤,
그 반대 페르소나에 맞는 8축 이상향 수치를 설계해주세요.

【페르소나 반대의 의미】
단순히 점수를 뒤집는 것이 아닙니다.
현재 페르소나가 추구하는 삶의 방식·가치관·소비 철학과 대비되는 새로운 정체성입니다.

페르소나 반대 예시:
- 실용적 성취자 → 무목적 탐험가 (결과보다 과정, 효율보다 우연한 발견을 즐김)
- 지적 탐험가 → 감각적 몰입자 (분석 없이 감정과 감각으로만 체험하는 사람)
- 감성 창조자 → 냉철한 분석가 (감정 배제, 논리·구조·데이터로 세계를 이해)
- 사회적 공감자 → 고독한 내면 탐구자 (타인 시선 배제, 자신만의 내면 세계에 집중)
- 가벼운 소비자 → 깊이 몰입 탐구자 (가볍게 소비하지 않고 한 주제를 완전히 정복)
- 균형 추구자 → 극단적 전문가 (모든 것을 조금씩이 아닌 하나에 완전히 올인)

【8축 설명】
- intellectual_curiosity (지적 호기심): 새로운 지식·개념 탐구 욕구
- self_improvement (자기계발): 성장·목표 달성 지향
- social_awareness (사회·시선): 사회 이슈·타인 관점 관심
- depth_immersion (깊이·몰입): 한 주제에 깊이 파고드는 성향
- practical_orientation (실용 지향): 실생활 적용 가능한 것 선호
- emotional_comfort (정서·위로): 힐링·공감·감성 콘텐츠 선호
- creative_expression (창의·표현): 창작·예술·독창적 표현 관심
- entertainment_release (오락·해방): 즐거움·스트레스 해소 추구

【설계 규칙】
1. 반대 페르소나 이름과 설명을 먼저 정한 뒤, 그 성격에 맞는 수치를 역산할 것
2. 반대 페르소나의 핵심 축(높은 축)이 현재 dominant 축과 달라야 함
3. 수치는 반대 페르소나의 성격을 충실히 반영할 것 (15~90 범위)
4. 단순 수치 반전 금지 — 반드시 페르소나 정체성에서 수치를 도출할 것
5. opposite_persona_name과 opposite_persona_desc을 반드시 반환할 것

【가이드 생성 규칙】
guide_steps는 이 반대 페르소나처럼 살기 위한 4주 실천 로드맵입니다.
- 반드시 4개 반환 (1주차~4주차)
- 각 주차는 반대 페르소나의 철학을 반영한 구체적 콘텐츠 행동
- 형식 예시: "1주차 [지적 호기심]: 알고리즘 추천 대신 직접 검색으로 새 채널 3개 발굴"
- 마지막 4주차는 항상 변화 확인 + 재설계 제안으로 마무리
"""


def generate_opposite_by_llm(
    current_radar: RadarChart,
    layer_b: Optional[ProfilerLayerB],
    top5_interests: list[str],
    dominant_axes: list[str],
) -> tuple[IdealRadarChart, Guide]:
    """
    페르소나 기반 3단계 반대방향 이상향 생성:
    ① 8각 데이터 → 페르소나 분류 (수식)
    ② 반대 페르소나 도출 + 수치 설계 (Gemini LLM)
    ③ IdealRadarChart 반환
    """
    # ① 페르소나 분류 (수식)
    current_persona = classify_persona(current_radar)

    # ② Gemini LLM 호출
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    ).with_structured_output(OppositeIdealResult)

    current_str = "\n".join(
        f"  {k.value} ({AXIS_META[k]['name']}): {v:.0f}"
        for k, v in current_radar.to_dict().items()
    )
    dominant_str = (
        ", ".join(f"{a}({AXIS_META[AxisKey(a)]['name']})" for a in dominant_axes)
        or "없음"
    )
    interests_str = ", ".join(top5_interests) if top5_interests else "미지정"

    layer_b_str = ""
    if layer_b:
        layer_b_str = (
            f"\n\n【Layer B 인지주권 지표】\n"
            f"  주체성: {layer_b.search_active_ratio:.2f} (낮으면 알고리즘 의존)\n"
            f"  채널편중도: {layer_b.viewing_concentration:.2f} (높을수록 나쁨)\n"
            f"  취향다양성: {layer_b.taste_diversity_index}\n"
            f"  탐색깊이: {layer_b.exploration_depth:.2f}"
        )

    user_prompt = (
        f"【현재 페르소나】\n"
        f"  이름: {current_persona['name']}\n"
        f"  설명: {current_persona['desc']}\n\n"
        f"【현재 8축 수치】\n{current_str}\n\n"
        f"【현재 dominant 축】 {dominant_str}\n"
        f"【TOP5 관심사】 {interests_str}"
        f"{layer_b_str}\n\n"
        f"'{current_persona['name']}' 페르소나와 삶의 방식·가치관이 반대인 페르소나를 정의하고, "
        f"그 반대 페르소나에 맞는 이상향 8축 수치를 설계해주세요."
    )

    result: OppositeIdealResult = llm.invoke(
        [
            {"role": "system", "content": _OPPOSITE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
    )

    scores = {
        AxisKey.INTELLECTUAL_CURIOSITY: _clamp(result.intellectual_curiosity),
        AxisKey.SELF_IMPROVEMENT: _clamp(result.self_improvement),
        AxisKey.SOCIAL_AWARENESS: _clamp(result.social_awareness),
        AxisKey.DEPTH_IMMERSION: _clamp(result.depth_immersion),
        AxisKey.PRACTICAL_ORIENTATION: _clamp(result.practical_orientation),
        AxisKey.EMOTIONAL_COMFORT: _clamp(result.emotional_comfort),
        AxisKey.CREATIVE_EXPRESSION: _clamp(result.creative_expression),
        AxisKey.ENTERTAINMENT_RELEASE: _clamp(result.entertainment_release),
    }

    # ③ 페르소나 전환 정보를 summary와 direction에 반영
    persona_summary = f"[{result.opposite_persona_name}] {result.summary}"
    direction = f"PERSONA:{current_persona['name']}→{result.opposite_persona_name}"

    ideal = _build_ideal(
        current_radar.user_id,
        IdealType.OPPOSITE,
        scores,
        summary=persona_summary,
        direction=direction,
        alpha=1.0,
    )
    ideal = ideal.model_copy(update={"reasoning": result.reasoning})

    # Guide 객체 생성 (LLM이 생성한 guide_steps 사용)
    guide = Guide(
        user_id=current_radar.user_id,
        title=f"{result.opposite_persona_name} 버블 탈출 30일 로드맵",
        steps=result.guide_steps,
        target_axes=[AxisKey(a) for a in dominant_axes if _is_valid_axis(a)],
        estimated_days=30,
    )

    return ideal, guide


def _is_valid_axis(axis: str) -> bool:
    try:
        AxisKey(axis)
        return True
    except ValueError:
        return False


# ──────────────────────────────────────────
# Mode 1 — DIRECT
# ──────────────────────────────────────────


def modify_direct(
    ideal: IdealRadarChart,
    axis: str,
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
        raise ValueError(f"알 수 없는 축: {axis}") from None

    clamped = _clamp(new_value)
    scores = ideal.to_dict()
    scores[axis_key] = clamped

    updated = _build_ideal(
        ideal.user_id,
        ideal.ideal_type,
        scores,
        ideal.summary,
        ideal.direction or "",
        ideal.alpha or 0.55,
    )

    # 연관 축 제안 (AXIS_VECTORS 기반, 모델 없이)
    suggestions: list[str] = []
    vectors = AXIS_VECTORS.get(axis_key, {})
    direction = "expansion" if ideal.ideal_type == IdealType.EXPANSION else "opposite"
    related = vectors.get(direction, {})
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
    f"  {key.value}: {meta['name']}" for key, meta in AXIS_META.items()
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
    ideal: IdealRadarChart,
    user_message: str,
    current_radar: Optional[RadarChart] = None,
    layer_b: Optional[ProfilerLayerB] = None,
) -> tuple[IdealRadarChart, ChatAdjustmentResult]:
    """
    자연어 메시지 → gpt-4o-mini → delta 추출 → ideal 업데이트

    Returns:
        (updated_ideal, result)  — result.reply를 유저에게 보여주세요
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
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

    result: ChatAdjustmentResult = llm.invoke(
        [
            {"role": "system", "content": _CHAT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
    )

    # delta 적용
    scores = ideal.to_dict()
    for adj in result.adjustments:
        try:
            key = AxisKey(adj.axis)
            scores[key] = _clamp(scores[key] + adj.delta)
        except ValueError:
            pass

    updated = _build_ideal(
        ideal.user_id,
        ideal.ideal_type,
        scores,
        ideal.summary,
        ideal.direction or "",
        ideal.alpha or 0.55,
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
    current_radar: RadarChart,
    layer_b: ProfilerLayerB,
    top5_interests: list[str],
    user_goal: Optional[str] = None,
) -> IdealRadarChart:
    """
    gpt-4o가 Layer A + Layer B + 목표를 종합 분석하여 최적 이상향 설계.

    Args:
        user_goal: 유저가 입력한 목표 텍스트 (선택)
    Returns:
        AI가 설계한 IdealRadarChart (ideal_type=custom)
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.5,
        api_key=os.getenv("OPENAI_API_KEY"),
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
    goal_str = f"\n유저 목표: {user_goal}" if user_goal else ""

    user_prompt = (
        f"【현재 프로필 Layer A】\n{current_str}\n\n"
        f"【Layer B 인지주권 지표】\n{layer_b_str}\n\n"
        f"【TOP5 관심사】 {interests_str}"
        f"{goal_str}\n\n"
        f"위 데이터를 바탕으로 최적의 이상향 8각 차트를 설계해주세요."
    )

    result: AutoIdealResult = llm.invoke(
        [
            {"role": "system", "content": _AUTO_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
    )

    scores = {
        AxisKey.INTELLECTUAL_CURIOSITY: _clamp(result.intellectual_curiosity),
        AxisKey.SELF_IMPROVEMENT: _clamp(result.self_improvement),
        AxisKey.SOCIAL_AWARENESS: _clamp(result.social_awareness),
        AxisKey.DEPTH_IMMERSION: _clamp(result.depth_immersion),
        AxisKey.PRACTICAL_ORIENTATION: _clamp(result.practical_orientation),
        AxisKey.EMOTIONAL_COMFORT: _clamp(result.emotional_comfort),
        AxisKey.CREATIVE_EXPRESSION: _clamp(result.creative_expression),
        AxisKey.ENTERTAINMENT_RELEASE: _clamp(result.entertainment_release),
    }

    ideal = _build_ideal(
        current_radar.user_id,
        IdealType.CUSTOM,
        scores,
        summary=result.summary,
        direction="AUTO_OPTIMAL",
        alpha=1.0,
    )
    ideal = ideal.model_copy(update={"reasoning": result.reasoning})
    return ideal
