"""
Navigator Agent - Tools
Dual-Layer 아키텍처 v1.1 핵심 계산 함수

- Layer B 파생 계산 제거 (Profiler v1.1이 담당)
- 8축 이중 방향(OPPOSITE + EXPANSION) 기반 이상향 생성
- dominant / weak 축 임계값(≥15) 적용
"""

from .schemas import (
    AXIS_META,
    AxisKey,
    Guide,
    IdealRadarChart,
    IdealType,
    ProfilerLayerB,
    ProfilerData,
    Quest,
    RadarChart,
    RadarComparison,
)


# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ──────────────────────────────────────────
# 8축 이중 방향 벡터 상수
#
# 각 축에 대해 OPPOSITE(반대) / EXPANSION(확장) 방향을 정의.
# 값은 α=1.0 일 때의 최대 변화량(절댓값).
# 실제 적용 시: delta * alpha 만큼 현재값에서 이동.
#
# ⚠️ 한 이상향에 여러 dominant 축 벡터가 같은 target을 가리켜도
#    _clamp(0,100)으로 자동 제한됨.
# ──────────────────────────────────────────


AXIS_VECTORS: dict[AxisKey, dict[str, dict[AxisKey, float]]] = {
    AxisKey.INTELLECTUAL_CURIOSITY: {
        # 반대: 넓은 탐색 → 한 주제 깊은 몰입
        "opposite":  {AxisKey.INTELLECTUAL_CURIOSITY: -40, AxisKey.DEPTH_IMMERSION: +20},
        # 확장: 지적 탐색 → 타문화·이종학문으로 더 넓게
        "expansion": {AxisKey.INTELLECTUAL_CURIOSITY: +28, AxisKey.SOCIAL_AWARENESS: +15},
    },
    AxisKey.SELF_IMPROVEMENT: {
        # 반대: 목표 지향 → 무목적 여유·놀이 소비
        "opposite":  {AxisKey.SELF_IMPROVEMENT: -35, AxisKey.ENTERTAINMENT_RELEASE: +25},
        # 확장: 자기계발 → 철학적 성찰·삶의 의미
        "expansion": {AxisKey.SELF_IMPROVEMENT: +28, AxisKey.DEPTH_IMMERSION: +15},
    },
    AxisKey.SOCIAL_AWARENESS: {
        # 반대: 사회·세상 → 내면·솔로·명상
        "opposite":  {AxisKey.SOCIAL_AWARENESS: -35, AxisKey.EMOTIONAL_COMFORT: +20},
        # 확장: 사회 관심 → 글로벌 시각·다문화
        "expansion": {AxisKey.SOCIAL_AWARENESS: +28, AxisKey.INTELLECTUAL_CURIOSITY: +15},
    },
    AxisKey.DEPTH_IMMERSION: {
        # 반대: 깊은 몰입 → 가볍고 다양한 탐색
        "opposite":  {AxisKey.DEPTH_IMMERSION: -35, AxisKey.ENTERTAINMENT_RELEASE: +20},
        # 확장: 몰입 → 전문가·학문적 깊이
        "expansion": {AxisKey.DEPTH_IMMERSION: +28, AxisKey.SELF_IMPROVEMENT: +15},
    },
    AxisKey.PRACTICAL_ORIENTATION: {
        # 반대: 실용 지향 → 순수 성찰·인문학
        "opposite":  {AxisKey.PRACTICAL_ORIENTATION: -35, AxisKey.INTELLECTUAL_CURIOSITY: +20},
        # 확장: 실용 스킬 → 고급 스킬·전문 마스터리
        "expansion": {AxisKey.PRACTICAL_ORIENTATION: +28, AxisKey.SELF_IMPROVEMENT: +15},
    },
    AxisKey.EMOTIONAL_COMFORT: {
        # 반대: 힐링·위로 → 도전·비판·불편한 진실
        "opposite":  {AxisKey.EMOTIONAL_COMFORT: -35, AxisKey.SELF_IMPROVEMENT: +20},
        # 확장: 정서 위로 → 다양한 감정 스펙트럼·예술
        "expansion": {AxisKey.EMOTIONAL_COMFORT: +28, AxisKey.CREATIVE_EXPRESSION: +15},
    },
    AxisKey.CREATIVE_EXPRESSION: {
        # 반대: 창작·표현 → 수용·감상·분석 위주
        "opposite":  {AxisKey.CREATIVE_EXPRESSION: -30, AxisKey.INTELLECTUAL_CURIOSITY: +20},
        # 확장: 창의 표현 → 다른 매체·협업 창작
        "expansion": {AxisKey.CREATIVE_EXPRESSION: +30, AxisKey.SOCIAL_AWARENESS: +15},
    },
    AxisKey.ENTERTAINMENT_RELEASE: {
        # 반대: 오락·해방 → 깊이·집중·진지한 콘텐츠
        "opposite":  {AxisKey.ENTERTAINMENT_RELEASE: -35, AxisKey.DEPTH_IMMERSION: +20},
        # 확장: 오락 → 다양한 장르·문화 오락
        "expansion": {AxisKey.ENTERTAINMENT_RELEASE: +28, AxisKey.SOCIAL_AWARENESS: +15},
    },
}

# 3단계 강도
ALPHA_LEVELS = {
    1: 0.25,   # Level 1 — 거부감 없는 변화 / 조금 더 넓게
    2: 0.55,   # Level 2 — 약간의 불편함 / 인접 분야까지
    3: 1.00,   # Level 3 — 완전히 다른 형태 / 새 영역 개척
}


# ──────────────────────────────────────────
# dominant / weak 축 계산
# ──────────────────────────────────────────


def compute_dominant_weak(
    layer_a: RadarChart,
    threshold: float = 15.0,
) -> tuple[list[str], list[str]]:
    """
    layer_a 점수에서 dominant(상위) / weak(하위) 축을 계산.

    threshold: 평균과의 차이가 이 값 이상인 축만 dominant / weak로 인정.
    → 점수가 비슷한 축끼리 dominant 지위가 매번 뒤집히는 불안정 방지.
    """
    scores: dict[str, float] = {k.value: v for k, v in layer_a.to_dict().items()}
    mean = sum(scores.values()) / len(scores)

    sorted_desc = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    sorted_asc  = sorted(scores.items(), key=lambda x: x[1])

    # 평균보다 threshold/2 이상 높은 상위 2개
    dominant = [
        k for k, v in sorted_desc[:2]
        if v >= mean + threshold / 2
    ]
    # 평균보다 threshold/2 이상 낮은 하위 2개
    weak = [
        k for k, v in sorted_asc[:2]
        if v <= mean - threshold / 2
    ]

    # 폴백: threshold 조건 미충족 시 상위/하위 1개씩 무조건 선택
    if not dominant:
        dominant = [sorted_desc[0][0]]
    if not weak:
        weak = [sorted_asc[0][0]]

    return dominant, weak


# ──────────────────────────────────────────
# 이중 방향 벡터 적용
# ──────────────────────────────────────────


def _apply_vectors(
    scores: dict[AxisKey, float],
    axes:   list[str],
    direction: str,
    alpha: float,
) -> dict[AxisKey, float]:
    """
    주어진 축 목록에 대해 direction 방향 벡터를 alpha 강도로 적용.
    """
    result = dict(scores)
    for axis_str in axes:
        try:
            axis_key = AxisKey(axis_str)
        except ValueError:
            continue
        vectors = AXIS_VECTORS[axis_key][direction]
        for target_key, delta in vectors.items():
            result[target_key] = _clamp(result[target_key] + delta * alpha)
    return result


def _build_ideal(
    user_id:    str,
    ideal_type: IdealType,
    scores:     dict[AxisKey, float],
    summary:    str,
    direction:  str = "",
    alpha:      float = 0.55,
) -> IdealRadarChart:
    return IdealRadarChart(
        user_id    = user_id,
        ideal_type = ideal_type,
        summary    = summary,
        direction  = direction,
        alpha      = alpha,
        intellectual_curiosity = round(scores[AxisKey.INTELLECTUAL_CURIOSITY], 1),
        self_improvement       = round(scores[AxisKey.SELF_IMPROVEMENT], 1),
        social_awareness       = round(scores[AxisKey.SOCIAL_AWARENESS], 1),
        depth_immersion        = round(scores[AxisKey.DEPTH_IMMERSION], 1),
        practical_orientation  = round(scores[AxisKey.PRACTICAL_ORIENTATION], 1),
        emotional_comfort      = round(scores[AxisKey.EMOTIONAL_COMFORT], 1),
        creative_expression    = round(scores[AxisKey.CREATIVE_EXPRESSION], 1),
        entertainment_release  = round(scores[AxisKey.ENTERTAINMENT_RELEASE], 1),
    )


# ──────────────────────────────────────────
# 이상향 3종 생성
# ──────────────────────────────────────────


def generate_opposite_ideal(
    current:       RadarChart,
    dominant_axes: list[str] | None = None,
    weak_axes:     list[str] | None = None,
    layer_b=None,
    top5_interests: list[str] | None = None,
) -> IdealRadarChart:
    """
    반대 방향형 이상향 — gpt-4o 기반 철학적 반대 방향 설계
    단순 수치 반전이 아닌 콘텐츠 소비 정체성의 대비를 표현.
    """
    from .modifier import generate_opposite_by_llm

    if dominant_axes is None:
        dominant_axes, _ = compute_dominant_weak(current)

    return generate_opposite_by_llm(
        current_radar  = current,
        layer_b        = layer_b,
        top5_interests = top5_interests or [],
        dominant_axes  = dominant_axes,
    )


def generate_expansion_ideal(
    current:       RadarChart,
    dominant_axes: list[str] | None = None,
    weak_axes:     list[str] | None = None,
    alpha:         float = ALPHA_LEVELS[2],   # Level 2 — 뚜렷한 확장
) -> IdealRadarChart:
    """
    확장 방향형 이상향 — 자연스러운 성장 (기본 추천)
    weak 축에 EXPANSION 벡터 적용 (α=0.55 — 뚜렷한 변화)
    """
    if weak_axes is None:
        _, weak_axes = compute_dominant_weak(current)

    scores = _apply_vectors(
        current.to_dict(), weak_axes, "expansion", alpha
    )
    dir_str = ", ".join(
        f"{a}→EXPANSION"
        for a in weak_axes
    )
    return _build_ideal(
        current.user_id, IdealType.EXPANSION, scores,
        "공백 분야 확장 — 자연스러운 성장, 부담 없는 변화",
        direction=dir_str, alpha=alpha,
    )


def generate_balanced_ideal(
    current: RadarChart,
) -> IdealRadarChart:
    """
    균형형 이상향 — 모든 축 50~65 수렴
    """
    s = current.to_dict()
    scores = {
        AxisKey.INTELLECTUAL_CURIOSITY: _clamp(max(s[AxisKey.INTELLECTUAL_CURIOSITY], 65)),
        AxisKey.SELF_IMPROVEMENT:       _clamp(max(s[AxisKey.SELF_IMPROVEMENT],       65)),
        AxisKey.SOCIAL_AWARENESS:       _clamp(max(s[AxisKey.SOCIAL_AWARENESS],       65)),
        AxisKey.DEPTH_IMMERSION:        _clamp(max(s[AxisKey.DEPTH_IMMERSION],        60)),
        AxisKey.CREATIVE_EXPRESSION:    _clamp(max(s[AxisKey.CREATIVE_EXPRESSION],    60)),
        AxisKey.PRACTICAL_ORIENTATION:  50.0,
        AxisKey.EMOTIONAL_COMFORT:      50.0,
        AxisKey.ENTERTAINMENT_RELEASE:  50.0,
    }
    return _build_ideal(
        current.user_id, IdealType.BALANCED, scores,
        "모든 축이 균형 잡힌 이상향 — 완전한 인지주권",
        direction="all→BALANCED", alpha=0.5,
    )


def generate_all_ideals(
    current:        RadarChart,
    dominant_axes:  list[str] | None = None,
    weak_axes:      list[str] | None = None,
    layer_b=None,
    top5_interests: list[str] | None = None,
) -> list[IdealRadarChart]:
    """이상향 3종 동시 생성 (반대 / 확장 / 균형)"""
    if dominant_axes is None or weak_axes is None:
        _dom, _weak = compute_dominant_weak(current)
        dominant_axes = dominant_axes or _dom
        weak_axes     = weak_axes     or _weak

    return [
        generate_opposite_ideal(current, dominant_axes, weak_axes, layer_b, top5_interests),
        generate_expansion_ideal(current, dominant_axes, weak_axes),
        generate_balanced_ideal(current),
    ]


# ──────────────────────────────────────────
# gap 계산
# ──────────────────────────────────────────


def compare_radar(current: RadarChart, ideal: IdealRadarChart) -> RadarComparison:
    return RadarComparison(
        user_id = current.user_id,
        current = current,
        ideal   = ideal,
    ).calculate_gap()


def get_priority_axes(comparison: RadarComparison, top_n: int = 3) -> list[AxisKey]:
    """gap 절댓값 큰 순서로 상위 N개 축 반환"""
    sorted_axes = sorted(
        comparison.gap.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    return [AxisKey(key) for key, _ in sorted_axes[:top_n]]


# ──────────────────────────────────────────
# 가이드 생성
# ──────────────────────────────────────────


_GUIDE_ACTIONS: dict[AxisKey, str] = {
    AxisKey.INTELLECTUAL_CURIOSITY: "{interest}와 연결된 새로운 분야 채널 주 2개씩 구독",
    AxisKey.SELF_IMPROVEMENT:       "{interest} 관련 루틴·습관 강의 하루 1편 완주",
    AxisKey.SOCIAL_AWARENESS:       "{interest}가 사회에 미치는 영향 뉴스·다큐 하루 1편",
    AxisKey.DEPTH_IMMERSION:        "{interest} 관련 20분↑ 장편 강의·다큐 하루 1편 완주",
    AxisKey.PRACTICAL_ORIENTATION:  "How-to 외 '{interest}의 왜' 철학·인문 콘텐츠 소비",
    AxisKey.EMOTIONAL_COMFORT:      "힐링 콘텐츠와 도전적 콘텐츠 교대 소비 (1:1 비율)",
    AxisKey.CREATIVE_EXPRESSION:    "{interest} 관련 창작·DIY 채널 탐색 및 따라 만들기",
    AxisKey.ENTERTAINMENT_RELEASE:  "오락 시간 제한 (하루 30분) + 남은 시간 깊이 콘텐츠",
}


def generate_guide(
    comparison:     RadarComparison,
    top5_interests: list[str],
) -> Guide:
    priority_axes = get_priority_axes(comparison, top_n=3)
    interest = top5_interests[0] if top5_interests else "관심 분야"
    interest_all = ", ".join(top5_interests) if top5_interests else "다양한 분야"

    steps: list[str] = []
    for i, axis_key in enumerate(priority_axes):
        week = i + 1
        action = _GUIDE_ACTIONS.get(axis_key, "다양한 콘텐츠 탐색")
        action = action.format(interest=interest, interest_all=interest_all)
        steps.append(f"{week}주차 [{AXIS_META[axis_key]['name']}]: {action}")

    steps.append("4주차 [종합]: 변화된 8각 차트 확인 + 다음 이상향 재설계")

    return Guide(
        user_id=comparison.user_id,
        title=(
            "·".join(AXIS_META[k]["name"] for k in priority_axes)
            + " 중심 버블 탈출 로드맵"
        ),
        steps=steps,
        target_axes=priority_axes,
        estimated_days=30,
    )


# ──────────────────────────────────────────
# 퀘스트 생성
# ──────────────────────────────────────────


_QUEST_TEMPLATES: dict[AxisKey, dict] = {
    AxisKey.INTELLECTUAL_CURIOSITY: {
        "title": "인접 분야 발견",
        "description": "{interest}와 연결된 새로운 분야 채널 1개 탐색",
        "action": "'{interest} + 다른 분야' 키워드로 유튜브 검색 후 새 채널 저장",
        "reward_point": 10,
    },
    AxisKey.SELF_IMPROVEMENT: {
        "title": "성장 콘텐츠 완주",
        "description": "{interest} 관련 자기계발 영상 1편 끝까지 보기",
        "action": "20분↑ 강의·루틴 영상 완주 후 핵심 1가지 메모",
        "reward_point": 20,
    },
    AxisKey.SOCIAL_AWARENESS: {
        "title": "세상 시선 넓히기",
        "description": "{interest}와 사회 이슈 연결 콘텐츠 1편 탐색",
        "action": "'{interest} 사회' 또는 '{interest} 뉴스' 검색 후 시청",
        "reward_point": 15,
    },
    AxisKey.DEPTH_IMMERSION: {
        "title": "깊이 들어가기",
        "description": "20분↑ 장편 콘텐츠 중단 없이 완주",
        "action": "{interest} 관련 강의·다큐·인터뷰 끝까지 시청",
        "reward_point": 20,
    },
    AxisKey.PRACTICAL_ORIENTATION: {
        "title": "왜? 라고 묻기",
        "description": "오늘은 How-to 대신 '{interest}의 철학' 탐색",
        "action": "'{interest} 왜' 또는 '{interest} 인문' 검색 후 시청",
        "reward_point": 10,
    },
    AxisKey.EMOTIONAL_COMFORT: {
        "title": "감성 균형 탐험",
        "description": "평소와 반대 무드 콘텐츠 1편 경험",
        "action": "힐링 콘텐츠 많이 보면 → 도전/토론 콘텐츠 1편, 반대도 동일",
        "reward_point": 10,
    },
    AxisKey.CREATIVE_EXPRESSION: {
        "title": "창작 탐험",
        "description": "{interest} 관련 창작·DIY 채널 1개 발견",
        "action": "'{interest} 만들기' 또는 '{interest} DIY' 검색 후 채널 저장",
        "reward_point": 15,
    },
    AxisKey.ENTERTAINMENT_RELEASE: {
        "title": "알고리즘 OFF",
        "description": "홈 피드 대신 검색창으로만 콘텐츠 찾기 10분",
        "action": "유튜브 홈 화면 열지 않고 검색 탭에서만 오늘의 영상 선택",
        "reward_point": 10,
    },
}


def generate_quests(
    comparison:     RadarComparison,
    top5_interests: list[str],
    count:          int = 3,
) -> list[Quest]:
    priority_axes = get_priority_axes(comparison, top_n=count)
    interest = top5_interests[0] if top5_interests else "관심 분야"
    quests: list[Quest] = []

    for axis_key in priority_axes:
        tmpl = _QUEST_TEMPLATES.get(axis_key)
        if not tmpl:
            continue
        quests.append(Quest(
            user_id      = comparison.user_id,
            title        = tmpl["title"],
            description  = tmpl["description"].format(interest=interest),
            target_axis  = axis_key,
            action       = tmpl["action"].format(interest=interest),
            reward_point = tmpl["reward_point"],
        ))

    return quests


# ──────────────────────────────────────────
# Layer B 신호 기반 퀘스트 보강
# ──────────────────────────────────────────


def enrich_quests_with_layer_b(
    quests:  list[Quest],
    layer_b: ProfilerLayerB,
) -> list[Quest]:
    """
    Layer B 지표가 낮은 경우 관련 퀘스트 reward_point 가중치 부여.

    ⚠️ viewing_concentration: 높을수록 나쁨 → 0.6 초과 시 경보
    """
    low_autonomy        = layer_b.search_active_ratio < 0.4
    high_concentration  = layer_b.viewing_concentration > 0.6   # 높을수록 나쁨
    low_diversity       = layer_b.taste_diversity_index < 50
    low_depth           = layer_b.exploration_depth < 0.4

    for q in quests:
        if low_autonomy and q.target_axis == AxisKey.ENTERTAINMENT_RELEASE:
            q.reward_point += 5
            q.title = q.title + " (주체성 UP)"
        if high_concentration and q.target_axis == AxisKey.INTELLECTUAL_CURIOSITY:
            q.reward_point += 5
            q.title = q.title + " (편중 해소)"
        if low_diversity and q.target_axis == AxisKey.SOCIAL_AWARENESS:
            q.reward_point += 5
            q.title = q.title + " (다양성 UP)"
        if low_depth and q.target_axis == AxisKey.DEPTH_IMMERSION:
            q.reward_point += 5
            q.title = q.title + " (탐색 깊이 UP)"

    return quests
