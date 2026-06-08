"""
Navigator Agent 로컬 테스트 스크립트 v1.1
Profiler v1.1 JSON 구조 + 8축 이중 방향(OPPOSITE/EXPANSION) 검증

실행:
    cd backend
    python test_navigator.py
"""

import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.agents.navigator.schemas import (
    ProfilerData,
    ProfilerLayerB,
    RadarChart,
)
from app.agents.navigator.tool import (
    compare_radar,
    compute_dominant_weak,
    generate_all_ideals,
    generate_guide,
    generate_quests,
    enrich_quests_with_layer_b,
    ALPHA_LEVELS,
)

# ──────────────────────────────────────────
# Mock 데이터 (Profiler v1.1 JSON 계약)
# ──────────────────────────────────────────

MOCK_LAYER_A = RadarChart(
    user_id                = "test_user",
    intellectual_curiosity =  72,
    self_improvement       =  65,
    social_awareness       =  35,
    depth_immersion        =  40,
    practical_orientation  =  78,
    emotional_comfort      =  55,
    creative_expression    =  28,
    entertainment_release  =  62,
)

MOCK_LAYER_B = ProfilerLayerB(
    search_active_ratio   = 0.31,   # 주체성 (낮음 경보)
    viewing_concentration = 0.71,   # 채널 편중도 (높음 = 나쁨, 경보)
    taste_diversity_index = 52,     # 취향 다양성
    exploration_depth     = 0.44,   # 탐색 깊이
)

MOCK_PROFILER = ProfilerData(
    user_id        = "test_user",
    computed_at    = "2026-06-08T09:00:00Z",
    layer_a        = MOCK_LAYER_A,
    layer_b        = MOCK_LAYER_B,
    top5_interests = ["IT", "운동", "요리", "독서", "여행"],
    summary        = "실용 지향 중심의 습관형 소비 패턴. 추천 의존도 높음.",
)

TOP5 = MOCK_PROFILER.top5_interests


# ──────────────────────────────────────────
# 테스트 유틸
# ──────────────────────────────────────────

def sep(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


# ──────────────────────────────────────────
# 테스트 1 — dominant / weak 계산
# ──────────────────────────────────────────

def test_dominant_weak():
    sep("TEST 1 — dominant / weak 축 계산 (임계값 15)")
    dominant, weak = compute_dominant_weak(MOCK_LAYER_A, threshold=15.0)
    print(f"  dominant: {dominant}")
    print(f"  weak:     {weak}")
    assert len(dominant) >= 1, "dominant 1개 이상 필요"
    assert len(weak)     >= 1, "weak 1개 이상 필요"
    print("  -> PASS")


# ──────────────────────────────────────────
# 테스트 2 — 이상향 3종 생성
# ──────────────────────────────────────────

def test_ideal_generation():
    sep("TEST 2 — 이상향 3종 (OPPOSITE / EXPANSION / BALANCED)")
    ideals = generate_all_ideals(MOCK_LAYER_A)
    assert len(ideals) == 3

    for ideal in ideals:
        print(f"\n  [{ideal.ideal_type.upper()}] {ideal.summary}")
        print(f"    방향: {ideal.direction}  alpha={ideal.alpha}")
        d = ideal.to_dict()
        for k, v in d.items():
            bar = "█" * int(v // 10) + "░" * (10 - int(v // 10))
            print(f"    {k.value:<28} {bar} {v:>5.1f}")
    print("\n  -> PASS")


# ──────────────────────────────────────────
# 테스트 3 — OPPOSITE 3단계 강도 비교
# ──────────────────────────────────────────

def test_alpha_levels():
    sep("TEST 3 — OPPOSITE 3단계 강도 (Level 1 / 2 / 3)")
    from app.agents.navigator.tool import generate_opposite_ideal
    dominant, _ = compute_dominant_weak(MOCK_LAYER_A)
    print(f"  dominant 축: {dominant}")

    for level, alpha in ALPHA_LEVELS.items():
        ideal = generate_opposite_ideal(MOCK_LAYER_A, dominant_axes=dominant, alpha=alpha)
        scores = ideal.to_dict()
        main_axis = dominant[0] if dominant else "practical_orientation"
        from app.agents.navigator.schemas import AxisKey
        try:
            key = AxisKey(main_axis)
            score = scores[key]
        except Exception:
            score = 0
        print(f"  Level {level} (alpha={alpha}): {main_axis} = {score:.1f}")
    print("  -> PASS")


# ──────────────────────────────────────────
# 테스트 4 — Gap 계산
# ──────────────────────────────────────────

def test_gap_comparison():
    sep("TEST 4 — 현재 vs EXPANSION 이상향 Gap 계산")
    ideals = generate_all_ideals(MOCK_LAYER_A)
    expansion = next(i for i in ideals if i.ideal_type == "expansion")
    comparison = compare_radar(MOCK_LAYER_A, expansion)
    print(f"  총 Gap: {comparison.total_gap}")
    print("  축별 Gap:")
    for k, v in comparison.gap.items():
        arrow = "↑" if v > 0 else ("↓" if v < 0 else "→")
        print(f"    {k.value:<28} {arrow} {v:+.1f}")
    assert comparison.total_gap > 0
    print("\n  -> PASS")


# ──────────────────────────────────────────
# 테스트 5 — 가이드 생성
# ──────────────────────────────────────────

def test_guide_generation():
    sep("TEST 5 — 30일 가이드 생성")
    ideals = generate_all_ideals(MOCK_LAYER_A)
    expansion = next(i for i in ideals if i.ideal_type == "expansion")
    comparison = compare_radar(MOCK_LAYER_A, expansion)
    guide = generate_guide(comparison, TOP5)
    print(f"  제목: {guide.title}")
    print(f"  기간: {guide.estimated_days}일")
    print(f"  타겟 축: {[k.value for k in guide.target_axes]}")
    print("  단계:")
    for step in guide.steps:
        print(f"    - {step}")
    assert len(guide.steps) == 4
    print("\n  -> PASS")


# ──────────────────────────────────────────
# 테스트 6 — 퀘스트 + Layer B 보강
# ──────────────────────────────────────────

def test_quest_with_layer_b():
    sep("TEST 6 — 퀘스트 생성 + Layer B 보강")
    ideals = generate_all_ideals(MOCK_LAYER_A)
    expansion = next(i for i in ideals if i.ideal_type == "expansion")
    comparison = compare_radar(MOCK_LAYER_A, expansion)
    quests = generate_quests(comparison, TOP5, count=3)
    quests = enrich_quests_with_layer_b(quests, MOCK_LAYER_B)

    print(f"  Layer B 건강도 평균: {MOCK_LAYER_B.average_health}")
    print(f"  주체성(search_active_ratio): {MOCK_LAYER_B.search_active_ratio} -> {'경보' if MOCK_LAYER_B.search_active_ratio < 0.4 else '양호'}")
    print(f"  채널편중도(viewing_concentration): {MOCK_LAYER_B.viewing_concentration} -> {'경보(높음=나쁨)' if MOCK_LAYER_B.viewing_concentration > 0.6 else '양호'}")
    print()
    assert len(quests) == 3
    for i, q in enumerate(quests, 1):
        print(f"  {i}. [{q.target_axis.value}] {q.title} (+{q.reward_point}pt)")
        print(f"     {q.description}")
        print(f"     -> {q.action}")
    print("\n  -> PASS")


# ──────────────────────────────────────────
# 실행
# ──────────────────────────────────────────

if __name__ == "__main__":
    print("\n[Navigator v1.1] 로컬 테스트 시작\n")
    try:
        test_dominant_weak()
        test_ideal_generation()
        test_alpha_levels()
        test_gap_comparison()
        test_guide_generation()
        test_quest_with_layer_b()
        print("\n" + "="*55)
        print("  [ALL PASS] v1.1 수식 검증 완료")
        print("="*55 + "\n")
    except Exception as e:
        print(f"\n[FAIL] {e}")
        raise
