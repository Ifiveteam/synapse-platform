/** 스크랩 문자열 카테고리 → 별자리 그래프 색상 */

const CONSTELLATION_FALLBACK = [
  "#3db8ff",
  "#ff88c8",
  "#c8e4ff",
  "#00d4ff",
  "#ff70c0",
  "#5088ff",
  "#b070ff",
  "#30e0e0",
  "#eab308",
  "#22c55e",
] as const;

function hashCategory(category: string): number {
  let hash = 0;
  for (let i = 0; i < category.length; i += 1) {
    hash = (hash * 31 + category.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function scrapCategoryColorMap(categories: string[]): Map<string, string> {
  const unique = [...new Set(categories.map((c) => c.trim()).filter(Boolean))].sort();
  const map = new Map<string, string>();
  for (const category of unique) {
    const idx = hashCategory(category) % CONSTELLATION_FALLBACK.length;
    map.set(category, CONSTELLATION_FALLBACK[idx]);
  }
  return map;
}
