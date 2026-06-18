import { BEHAVIOR_SPIDER_AXES } from "@/lib/analyses/behavior-spider";
import { TEMPERAMENT_AXES } from "@/lib/analyses/temperament";
import { VALUES_AXES } from "@/lib/analyses/values";

export const ALL_SCORE_AXES = [
  ...VALUES_AXES.map((a) => ({ ...a, group: "values" as const })),
  ...TEMPERAMENT_AXES.map((a) => ({ ...a, group: "temperament" as const })),
  ...BEHAVIOR_SPIDER_AXES.map((a) => ({ ...a, group: "behavior" as const })),
];

const LABEL_BY_KEY = Object.fromEntries(
  ALL_SCORE_AXES.map(({ key, label }) => [key, label]),
);

export function scoreAxisLabel(key: string): string {
  return LABEL_BY_KEY[key] ?? key;
}

export const SCORE_GROUP_LABELS = {
  values: "가치관",
  temperament: "기질",
  behavior: "행동 성향",
} as const;
