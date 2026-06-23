import type { SynapseAxisKey } from "@/api/types/profiler";

export const AXIS_LABELS: Record<SynapseAxisKey, string> = {
  intellectual_curiosity: "지적 호기심",
  practical_orientation: "실용 지향",
  emotional_comfort: "정서·위로",
  social_awareness: "사회·시선",
  creative_expression: "창의·표현",
  entertainment_release: "오락·해방",
  self_improvement: "자기계발",
  depth_immersion: "깊이·몰입",
};

export const LAYER_B_LABELS: Record<string, string> = {
  search_active_ratio: "주체성",
  viewing_concentration: "채널 편중도",
  taste_diversity_index: "취향 다양성",
  exploration_depth: "탐색 깊이",
};

export function formatPercent(value: number, asPoints = false): string {
  if (asPoints) {
    return `${value >= 0 ? "+" : ""}${value.toFixed(0)}점`;
  }
  return `${(value * 100).toFixed(0)}%`;
}
