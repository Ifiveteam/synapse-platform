/** Schwartz 가치관 10축 — user_profile_history 점수 키 */

export const VALUES_AXES = [
  { key: "self_direction", label: "자기지향" },
  { key: "stimulation", label: "자극" },
  { key: "achievement", label: "성취" },
  { key: "power", label: "권력" },
  { key: "security", label: "안전" },
  { key: "benevolence", label: "친선" },
  { key: "universalism", label: "보편" },
  { key: "hedonism", label: "쾌락" },
  { key: "conformity", label: "순응" },
  { key: "tradition", label: "전통" },
] as const;

export function valuesBarData(scores: Record<string, number>) {
  return VALUES_AXES.map(({ key, label }) => ({
    key,
    label,
    value: Math.round(Math.max(0, Math.min(100, scores[key] ?? 0))),
  }));
}
