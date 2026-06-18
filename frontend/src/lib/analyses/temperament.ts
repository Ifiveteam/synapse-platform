/** TCI 기질 3축 — user_profile_history 점수 키 */

export const TEMPERAMENT_AXES = [
  { key: "novelty_seeking", label: "탐구성" },
  { key: "persistence", label: "지속성" },
  { key: "self_transcendence", label: "자기초월" },
] as const;

export function temperamentBarData(scores: Record<string, number>) {
  return TEMPERAMENT_AXES.map(({ key, label }) => ({
    key,
    label,
    value: Math.round(Math.max(0, Math.min(100, scores[key] ?? 0))),
  }));
}
