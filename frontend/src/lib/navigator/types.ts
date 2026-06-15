// ──────────────────────────────────────────
// Navigator Dual-Layer Types — v1.1
// ──────────────────────────────────────────

/** Layer A — Profiler 8각 (Profiler v1.1) */
export interface RadarChart {
  user_id: string;
  intellectual_curiosity: number;  // 지적 호기심
  self_improvement: number;        // 자기계발
  social_awareness: number;        // 사회·시선
  depth_immersion: number;         // 깊이·몰입
  practical_orientation: number;   // 실용 지향
  emotional_comfort: number;       // 정서·위로
  creative_expression: number;     // 창의·표현
  entertainment_release: number;   // 오락·해방
}

export type AxisKey = keyof Omit<RadarChart, "user_id">;

export const AXIS_LABELS: Record<AxisKey, string> = {
  intellectual_curiosity: "지적 호기심",
  self_improvement:       "자기계발",
  social_awareness:       "사회·시선",
  depth_immersion:        "깊이·몰입",
  practical_orientation:  "실용 지향",
  emotional_comfort:      "정서·위로",
  creative_expression:    "창의·표현",
  entertainment_release:  "오락·해방",
};

// 레이더 차트 색상용 (이중 방향 도입 후에도 시각화 목적으로 유지)
export type AxisType = "GROWTH" | "EXPANSION" | "FLEXIBLE";

export const AXIS_TYPES: Record<AxisKey, AxisType> = {
  intellectual_curiosity: "GROWTH",
  self_improvement:       "GROWTH",
  social_awareness:       "GROWTH",
  depth_immersion:        "EXPANSION",
  practical_orientation:  "FLEXIBLE",
  emotional_comfort:      "FLEXIBLE",
  creative_expression:    "EXPANSION",
  entertainment_release:  "FLEXIBLE",
};

export const AXIS_TYPE_COLOR: Record<AxisType, string> = {
  GROWTH:    "text-emerald-600",
  EXPANSION: "text-violet-600",
  FLEXIBLE:  "text-amber-600",
};

/** 8축 이중 방향 설명 */
export const AXIS_DIRECTIONS: Record<
  AxisKey,
  { opposite: string; expansion: string }
> = {
  intellectual_curiosity: {
    opposite:  "한 주제 깊은 몰입 (breadth → depth)",
    expansion: "타문화·이종학문으로 더 넓게",
  },
  self_improvement: {
    opposite:  "무목적 여유·놀이 소비",
    expansion: "철학적 성찰·삶의 의미 탐구",
  },
  social_awareness: {
    opposite:  "내면·솔로·명상 콘텐츠",
    expansion: "글로벌 시각·다문화 이해",
  },
  depth_immersion: {
    opposite:  "가볍고 다양한 탐색",
    expansion: "전문가·학문적 깊이",
  },
  practical_orientation: {
    opposite:  "순수 성찰·인문학",
    expansion: "고급 스킬·전문 기술 마스터리",
  },
  emotional_comfort: {
    opposite:  "도전·비판·불편한 진실",
    expansion: "다양한 감정 스펙트럼·예술",
  },
  creative_expression: {
    opposite:  "수용·감상·분석 위주",
    expansion: "다른 매체·협업 창작",
  },
  entertainment_release: {
    opposite:  "깊이·집중·진지한 콘텐츠",
    expansion: "다양한 장르·문화 오락",
  },
};

/**
 * Layer B — 인지주권 4지표 (Profiler v1.1 산출)
 *
 * ⚠️ viewing_concentration: 높을수록 나쁨 (소수 채널 편중)
 *    나머지 3개: 높을수록 좋음
 */
export interface ProfilerLayerB {
  search_active_ratio:   number;  // 0~1, 높을수록 좋음  — 주체성
  viewing_concentration: number;  // 0~1, 높을수록 나쁨  — 채널 편중도
  taste_diversity_index: number;  // 0~100, 높을수록 좋음 — 취향 다양성
  exploration_depth:     number;  // 0~1, 높을수록 좋음  — 탐색 깊이
}

export type LayerBKey = keyof ProfilerLayerB;

export const LAYER_B_META: Record<
  LayerBKey,
  {
    label: string;
    description: string;
    icon: string;
    unit: "ratio" | "score";
    /** true면 높을수록 나쁨 — 게이지 색상·이상향 방향 반전 */
    invertedPolarity: boolean;
    warnThreshold: number;  // 경보 기준값 (invertedPolarity=true면 이 값 초과 시 경보)
  }
> = {
  search_active_ratio: {
    label:           "주체성",
    description:     "직접 검색·탐색 vs 추천·습관 소비 비율",
    icon:            "🧭",
    unit:            "ratio",
    invertedPolarity: false,
    warnThreshold:   0.4,
  },
  viewing_concentration: {
    label:           "채널 편중도",
    description:     "시청이 소수 채널에 몰리는 정도",
    icon:            "📺",
    unit:            "ratio",
    invertedPolarity: true,   // 높을수록 나쁨
    warnThreshold:   0.6,
  },
  taste_diversity_index: {
    label:           "취향 다양성",
    description:     "취향 4종(지적·사회·실용·정서) 분산 정도",
    icon:            "🎨",
    unit:            "score",
    invertedPolarity: false,
    warnThreshold:   50,
  },
  exploration_depth: {
    label:           "탐색 깊이",
    description:     "새 주제 진입 시 얼마나 깊게 탐색하는가",
    icon:            "🔍",
    unit:            "ratio",
    invertedPolarity: false,
    warnThreshold:   0.4,
  },
};

/** 이상향 타입 (v1.1: adjacent → expansion) */
export type IdealType = "opposite" | "expansion" | "balanced";

export const IDEAL_META: Record<
  IdealType,
  { label: string; description: string; color: string; borderColor: string; recommended?: boolean }
> = {
  opposite: {
    label:       "반대 방향형",
    description: "dominant 축을 반대로 — 필터버블 완전 탈출",
    color:       "bg-rose-50",
    borderColor: "border-rose-300",
  },
  expansion: {
    label:       "확장 방향형",
    description: "공백 축을 자연스럽게 확장 — 부담 없는 성장",
    color:       "bg-blue-50",
    borderColor: "border-blue-400",
    recommended: true,
  },
  balanced: {
    label:       "균형형",
    description: "모든 축을 50~65로 수렴 — 완전한 인지주권",
    color:       "bg-emerald-50",
    borderColor: "border-emerald-300",
  },
};

export interface IdealRadarChart extends Omit<RadarChart, "user_id"> {
  user_id:   string;
  ideal_type: IdealType;
  summary:   string;
  direction?: string;
  alpha?:    number;
  /** AI 설계 근거 (AUTO 모드 전용) */
  reasoning?: string;
}

/** Profiler v1.1 전체 출력 */
export interface ProfilerData {
  user_id:        string;
  computed_at?:   string;
  layer_a:        RadarChart;
  layer_b:        ProfilerLayerB;
  top5_interests: string[];
  summary:        string;
}

/** 가이드 & 퀘스트 */
export interface Guide {
  user_id:        string;
  title:          string;
  steps:          string[];
  target_axes:    AxisKey[];
  estimated_days: number;
}

export interface Quest {
  user_id:      string;
  title:        string;
  description:  string;
  target_axis:  AxisKey;
  action:       string;
  reward_point: number;
  is_completed: boolean;
}
