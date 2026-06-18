export const HABIT_METRICS = [
  {
    key: "channel_concentration",
    label: "채널 편중도",
    hint: "상위 채널 시청 비중",
    higherIsBetter: false,
  },
  {
    key: "category_concentration",
    label: "카테고리 편중도",
    hint: "상위 카테고리 시청 비중",
    higherIsBetter: false,
  },
  {
    key: "category_diversity",
    label: "카테고리 다양성",
    hint: "시청 카테고리 폭",
    higherIsBetter: true,
  },
  {
    key: "exploration_depth",
    label: "탐색 깊이",
    hint: "채널 분산 정도",
    higherIsBetter: true,
  },
] as const;

export type HabitMetricKey = (typeof HABIT_METRICS)[number]["key"];

export interface HabitMetrics {
  channel_concentration: number;
  category_concentration: number;
  category_diversity: number;
  exploration_depth: number;
}

export function formatHabitPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatHabitDelta(delta: number): string {
  const pct = Math.round(delta * 100);
  if (pct === 0) return "0%p";
  return `${pct > 0 ? "+" : ""}${pct}%p`;
}
