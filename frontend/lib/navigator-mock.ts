/**
 * Navigator 데모용 Mock 데이터 — Profiler v1.1
 * 실제 Profiler 연동 전 UI 개발·테스트용
 */
import type {
  Guide,
  IdealRadarChart,
  ProfilerData,
  Quest,
} from "./navigator-types";

export const MOCK_PROFILER_DATA: ProfilerData = {
  user_id:     "demo_user",
  computed_at: "2026-06-08T09:00:00Z",

  layer_a: {
    user_id:                "demo_user",
    intellectual_curiosity:  72,
    self_improvement:        65,
    social_awareness:        35,
    depth_immersion:         40,
    practical_orientation:   78,
    emotional_comfort:       55,
    creative_expression:     28,
    entertainment_release:   62,
  },

  layer_b: {
    search_active_ratio:   0.31,   // 주체성 — 낮음 경보
    viewing_concentration: 0.71,   // 채널 편중도 — 높음=나쁨 경보
    taste_diversity_index: 52,     // 취향 다양성
    exploration_depth:     0.44,   // 탐색 깊이
  },

  top5_interests: ["IT", "운동", "요리", "독서", "여행"],
  summary: "실용 지향 중심의 습관형 소비 패턴. 추천 의존도 높음.",
};

// ── 이상향 3종 (8축 이중 방향 기반) ──────────────

/** 반대 방향형: dominant(실용지향, 오락해방) OPPOSITE α=0.55 */
export const MOCK_IDEAL_OPPOSITE: IdealRadarChart = {
  user_id:                "demo_user",
  ideal_type:             "opposite",
  intellectual_curiosity:  83,   // practical_orientation OPPOSITE → intellectual_curiosity↑
  self_improvement:        65,
  social_awareness:        35,
  depth_immersion:         73,   // entertainment_release OPPOSITE → depth_immersion↑
  practical_orientation:   58,   // OPPOSITE: 78 - 35×0.55
  emotional_comfort:       55,
  creative_expression:     28,
  entertainment_release:   43,   // OPPOSITE: 62 - 35×0.55
  summary:                 "현재와 반대 방향 — 필터버블 탈출, 새로운 자아 발견",
  direction:               "practical_orientation→OPPOSITE, entertainment_release→OPPOSITE",
  alpha:                   0.55,
};

/** 확장 방향형: weak(창의표현, 사회시선) EXPANSION α=0.25 */
export const MOCK_IDEAL_EXPANSION: IdealRadarChart = {
  user_id:                "demo_user",
  ideal_type:             "expansion",
  intellectual_curiosity:  76,   // social_awareness EXPANSION → intellectual_curiosity↑
  self_improvement:        65,
  social_awareness:        42,   // EXPANSION: 35 + 28×0.25
  depth_immersion:         40,
  practical_orientation:   78,
  emotional_comfort:       55,
  creative_expression:     36,   // EXPANSION: 28 + 30×0.25
  entertainment_release:   62,
  summary:                 "공백 분야 확장 — 자연스러운 성장, 부담 없는 변화",
  direction:               "creative_expression→EXPANSION, social_awareness→EXPANSION",
  alpha:                   0.25,
};

/** 균형형: 전 축 50~65 수렴 */
export const MOCK_IDEAL_BALANCED: IdealRadarChart = {
  user_id:                "demo_user",
  ideal_type:             "balanced",
  intellectual_curiosity:  72,
  self_improvement:        65,
  social_awareness:        65,
  depth_immersion:         60,
  practical_orientation:   50,
  emotional_comfort:       50,
  creative_expression:     60,
  entertainment_release:   50,
  summary:                 "모든 축이 균형 잡힌 이상향 — 완전한 인지주권",
  direction:               "all→BALANCED",
  alpha:                   0.5,
};

// ── 가이드 & 퀘스트 ────────────────────────────

export const MOCK_GUIDE: Guide = {
  user_id:        "demo_user",
  title:          "창의·표현 · 사회·시선 · 깊이·몰입 중심 버블 탈출 로드맵",
  estimated_days: 30,
  target_axes:    ["creative_expression", "social_awareness", "depth_immersion"],
  steps: [
    "1주차 [창의·표현]: IT 관련 창작·DIY 채널 1개 발견 및 구독",
    "2주차 [사회·시선]: IT가 사회에 미치는 영향 뉴스·다큐 하루 1편",
    "3주차 [깊이·몰입]: IT 관련 20분↑ 장편 강의·다큐 하루 1편 완주",
    "4주차 [종합]: 변화된 8각 차트 확인 + 다음 이상향 재설계",
  ],
};

export const MOCK_QUESTS: Quest[] = [
  {
    user_id:      "demo_user",
    title:        "창작 탐험",
    description:  "IT 관련 창작·DIY 채널 1개 발견",
    target_axis:  "creative_expression",
    action:       "'IT 만들기' 또는 'IT DIY' 검색 후 채널 저장",
    reward_point: 15,
    is_completed: false,
  },
  {
    user_id:      "demo_user",
    title:        "세상 시선 넓히기 (다양성 UP)",
    description:  "IT와 사회 이슈 연결 콘텐츠 1편 탐색",
    target_axis:  "social_awareness",
    action:       "'IT 사회' 또는 'IT 뉴스' 검색 후 시청",
    reward_point: 20,
    is_completed: false,
  },
  {
    user_id:      "demo_user",
    title:        "알고리즘 OFF (주체성 UP)",
    description:  "홈 피드 대신 검색창으로만 콘텐츠 찾기 10분",
    target_axis:  "entertainment_release",
    action:       "유튜브 홈 화면 열지 않고 검색 탭에서만 오늘의 영상 선택",
    reward_point: 15,
    is_completed: false,
  },
];
