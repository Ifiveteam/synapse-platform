"""
Navigator Agent - Tools
이상향 생성, 가이드, 퀘스트 관련 핵심 툴
"""

from .schemas import (
    AXIS_META,
    AxisKey,
    AxisType,
    Guide,
    IdealRadarChart,
    IdealType,
    Quest,
    RadarChart,
    RadarComparison,
)


# ──────────────────────────────────────────
# 이상향 자동 생성 (수식 기반)
# ──────────────────────────────────────────

GROWTH_BOOST = 25       # 성장축: +25점
EXPANSION_BOOST = 20    # 확장축: +20점
SPECTRUM_TARGET = 50    # 스펙트럼축: 중간값으로 수렴
BIAS_THRESHOLD = 30     # 치우침 판단 임계값


def _clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
    return max(min_val, min(max_val, value))


def generate_opposite_ideal(current: RadarChart) -> IdealRadarChart:
    """
    반대 성향형 이상향
    - 성장축: 최대한 높이기
    - 스펙트럼축: 반대 극단으로
    - 확장축: 현재 + boost
    """
    scores = current.to_dict()
    ideal = {}

    for key, score in scores.items():
        meta = AXIS_META[key]
        axis_type = meta["type"]

        if axis_type == AxisType.GROWTH:
            ideal[key] = _clamp(score + GROWTH_BOOST + 10)
        elif axis_type == AxisType.EXPANSION:
            ideal[key] = _clamp(score + EXPANSION_BOOST + 10)
        elif axis_type == AxisType.SPECTRUM:
            # 반대 극단으로 이동
            if score < 50:
                ideal[key] = _clamp(score + 40)   # 낮으면 높게
            else:
                ideal[key] = _clamp(score - 40)   # 높으면 낮게

    return IdealRadarChart(
        user_id=current.user_id,
        ideal_type=IdealType.OPPOSITE,
        perspective_balance=ideal[AxisKey.PERSPECTIVE_BALANCE],
        autonomy=ideal[AxisKey.AUTONOMY],
        exploration_width=ideal[AxisKey.EXPLORATION_WIDTH],
        depth_immersion=ideal[AxisKey.DEPTH_IMMERSION],
        emotional_challenge=ideal[AxisKey.EMOTIONAL_CHALLENGE],
        practical_reflection=ideal[AxisKey.PRACTICAL_REFLECTION],
        individual_social=ideal[AxisKey.INDIVIDUAL_SOCIAL],
        consume_create=ideal[AxisKey.CONSUME_CREATE],
        summary="현재와 반대 방향 - 필터버블을 완전히 탈출하는 이상향",
    )


def generate_adjacent_ideal(current: RadarChart) -> IdealRadarChart:
    """
    인접 확장형 이상향
    - 성장축: 자연스럽게 올리기
    - 스펙트럼축: 치우친 경우만 중간으로 부드럽게
    - 확장축: 현재 + 작은 boost
    """
    scores = current.to_dict()
    ideal = {}

    for key, score in scores.items():
        meta = AXIS_META[key]
        axis_type = meta["type"]

        if axis_type == AxisType.GROWTH:
            ideal[key] = _clamp(score + GROWTH_BOOST)
        elif axis_type == AxisType.EXPANSION:
            ideal[key] = _clamp(score + EXPANSION_BOOST)
        elif axis_type == AxisType.SPECTRUM:
            # 치우친 경우만 중간 방향으로 살짝
            if score < BIAS_THRESHOLD:
                ideal[key] = _clamp(score + 20)
            elif score > (100 - BIAS_THRESHOLD):
                ideal[key] = _clamp(score - 20)
            else:
                ideal[key] = score  # 균형 상태면 유지

    return IdealRadarChart(
        user_id=current.user_id,
        ideal_type=IdealType.ADJACENT,
        perspective_balance=ideal[AxisKey.PERSPECTIVE_BALANCE],
        autonomy=ideal[AxisKey.AUTONOMY],
        exploration_width=ideal[AxisKey.EXPLORATION_WIDTH],
        depth_immersion=ideal[AxisKey.DEPTH_IMMERSION],
        emotional_challenge=ideal[AxisKey.EMOTIONAL_CHALLENGE],
        practical_reflection=ideal[AxisKey.PRACTICAL_REFLECTION],
        individual_social=ideal[AxisKey.INDIVIDUAL_SOCIAL],
        consume_create=ideal[AxisKey.CONSUME_CREATE],
        summary="현재에서 자연스럽게 성장 - 부담 없는 인접 확장",
    )


def generate_balanced_ideal(current: RadarChart) -> IdealRadarChart:
    """
    밸런스형 이상향
    - 성장축: 최대값으로
    - 스펙트럼축: 모두 50(중간)으로
    - 확장축: 70 목표
    """
    return IdealRadarChart(
        user_id=current.user_id,
        ideal_type=IdealType.BALANCED,
        perspective_balance=_clamp(max(current.perspective_balance, 70)),
        autonomy=_clamp(max(current.autonomy, 70)),
        exploration_width=_clamp(max(current.exploration_width, 65)),
        depth_immersion=_clamp(max(current.depth_immersion, 65)),
        emotional_challenge=50.0,
        practical_reflection=50.0,
        individual_social=50.0,
        consume_create=50.0,
        summary="모든 축이 균형 잡힌 이상향 - 완전한 인지주권",
    )


def generate_all_ideals(current: RadarChart) -> list[IdealRadarChart]:
    """3가지 이상향 동시 생성"""
    return [
        generate_opposite_ideal(current),
        generate_adjacent_ideal(current),
        generate_balanced_ideal(current),
    ]


# ──────────────────────────────────────────
# 이상향 비교
# ──────────────────────────────────────────


def compare_radar(current: RadarChart, ideal: IdealRadarChart) -> RadarComparison:
    """현재 vs 이상향 gap 계산"""
    comparison = RadarComparison(
        user_id=current.user_id,
        current=current,
        ideal=ideal,
    )
    return comparison.calculate_gap()


def get_priority_axes(comparison: RadarComparison, top_n: int = 3) -> list[AxisKey]:
    """gap이 큰 축 순서로 반환 (이상향까지 거리가 먼 축)"""
    sorted_axes = sorted(
        comparison.gap.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    return [AxisKey(key) for key, _ in sorted_axes[:top_n]]


# ──────────────────────────────────────────
# 가이드 생성
# ──────────────────────────────────────────


def generate_guide(
    comparison: RadarComparison,
    top5_interests: list[str],
) -> Guide:
    """
    현재 vs 이상향 gap 기반 버블 탈출 로드맵 생성
    gap이 큰 축 우선순위로 4주 가이드 생성
    """
    priority_axes = get_priority_axes(comparison, top_n=3)
    interest_str = ", ".join(top5_interests) if top5_interests else "다양한 분야"

    # 축별 가이드 액션 매핑
    axis_actions: dict[AxisKey, str] = {
        AxisKey.PERSPECTIVE_BALANCE: f"{interest_str} 관련 반대 의견 콘텐츠 하루 1개 시청",
        AxisKey.AUTONOMY: "알고리즘 추천 대신 직접 검색으로 콘텐츠 찾기",
        AxisKey.EXPLORATION_WIDTH: f"{interest_str}와 연결된 새로운 분야 채널 구독",
        AxisKey.DEPTH_IMMERSION: "15분 이상 짧은 영상 대신 심층 강의/다큐 시청",
        AxisKey.EMOTIONAL_CHALLENGE: "힐링 콘텐츠와 도전적 콘텐츠 번갈아가며 소비",
        AxisKey.PRACTICAL_REFLECTION: "방법론 콘텐츠와 철학/인문 콘텐츠 균형있게 소비",
        AxisKey.INDIVIDUAL_SOCIAL: "개인 관심사 + 사회 이슈 콘텐츠 함께 소비",
        AxisKey.CONSUME_CREATE: "시청만 하지 않고 스크랩 + 메모 + 직접 탐색 시도",
    }

    steps = []
    for i, axis_key in enumerate(priority_axes):
        week = i + 1
        action = axis_actions.get(axis_key, "다양한 콘텐츠 탐색")
        axis_name = AXIS_META[axis_key]["name"]
        steps.append(f"{week}주차 [{axis_name}]: {action}")

    # 4주차 종합 정리
    steps.append("4주차 [종합]: 변화된 나의 8각 차트 확인 및 다음 이상향 재설계")

    return Guide(
        user_id=comparison.user_id,
        title=f"{'·'.join(AXIS_META[k]['name'] for k in priority_axes)} 중심 성장 로드맵",
        steps=steps,
        target_axes=priority_axes,
        estimated_days=30,
    )


# ──────────────────────────────────────────
# 퀘스트 생성
# ──────────────────────────────────────────


def generate_quests(
    comparison: RadarComparison,
    top5_interests: list[str],
    count: int = 3,
) -> list[Quest]:
    """
    gap이 큰 축 기반 오늘의 퀘스트 생성
    """
    priority_axes = get_priority_axes(comparison, top_n=count)
    interest_str = top5_interests[0] if top5_interests else "관심 분야"
    quests = []

    quest_templates: dict[AxisKey, dict] = {
        AxisKey.PERSPECTIVE_BALANCE: {
            "title": "반대 의견 탐험",
            "description": f"{interest_str}에 대한 반대 입장 영상 1개 시청하기",
            "action": f"유튜브에서 '{interest_str} 반론' 또는 '{interest_str} 단점' 검색",
            "reward_point": 15,
        },
        AxisKey.AUTONOMY: {
            "title": "알고리즘 OFF 탐색",
            "description": "추천 피드 대신 직접 검색으로 새로운 콘텐츠 찾기",
            "action": "홈 피드를 보지 않고 검색창에서만 콘텐츠 탐색 10분",
            "reward_point": 10,
        },
        AxisKey.EXPLORATION_WIDTH: {
            "title": "인접 분야 발견",
            "description": f"{interest_str}와 연결된 새로운 분야 채널 1개 찾기",
            "action": f"'{interest_str}' 관련 다른 분야 채널 구독 또는 저장",
            "reward_point": 10,
        },
        AxisKey.DEPTH_IMMERSION: {
            "title": "깊이 들어가기",
            "description": "20분 이상 심층 콘텐츠 완주하기",
            "action": f"{interest_str} 관련 강의/다큐/인터뷰 영상 끝까지 시청",
            "reward_point": 20,
        },
        AxisKey.EMOTIONAL_CHALLENGE: {
            "title": "반대 감성 경험",
            "description": "평소 안 보던 감성/도전 콘텐츠 1개 시청",
            "action": "평소 패턴 반대의 무드 콘텐츠 경험하기",
            "reward_point": 10,
        },
        AxisKey.PRACTICAL_REFLECTION: {
            "title": "생각의 전환",
            "description": "방법론/철학 관점 콘텐츠 균형있게 소비",
            "action": f"{interest_str}의 '왜'를 다루는 인문/철학 콘텐츠 1개",
            "reward_point": 10,
        },
        AxisKey.INDIVIDUAL_SOCIAL: {
            "title": "시선 확장",
            "description": "내 관심사가 사회에 미치는 영향 콘텐츠 탐색",
            "action": f"{interest_str}와 사회 이슈 연결된 뉴스/다큐 1개",
            "reward_point": 15,
        },
        AxisKey.CONSUME_CREATE: {
            "title": "능동 탐구",
            "description": "시청 후 스크랩 + 한 줄 메모 남기기",
            "action": "오늘 본 콘텐츠 중 1개 스크랩하고 생각 메모",
            "reward_point": 10,
        },
    }

    for axis_key in priority_axes:
        template = quest_templates.get(axis_key)
        if template:
            quests.append(
                Quest(
                    user_id=comparison.user_id,
                    title=template["title"],
                    description=template["description"],
                    target_axis=axis_key,
                    action=template["action"],
                    reward_point=template["reward_point"],
                )
            )

    return quests
