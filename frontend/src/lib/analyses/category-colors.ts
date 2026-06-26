/** 카테고리별 산점도 색상 — YouTube categoryId 고정 매핑 우선 */

const CATEGORY_ID_COLORS: Record<string, string> = {
  "1": "#a855f7",
  "10": "#ec4899",
  "17": "#ef4444",
  "20": "#f97316",
  "22": "#22c55e",
  "23": "#eab308",
  "24": "#06b6d4",
  "25": "#3b82f6",
  "27": "#6366f1",
  "28": "#14b8a6",
};

const FALLBACK_PALETTE = [
  "#8b5cf6",
  "#34d399",
  "#fb923c",
  "#38bdf8",
  "#f472b6",
  "#facc15",
  "#94a3b8",
] as const;

/** 별자리 그래프 — 선명한 하늘·핑크·시안 별 */
const CONSTELLATION_STAR_COLORS: Record<string, string> = {
  "1": "#ff70c0",
  "10": "#ff58b0",
  "17": "#3db8ff",
  "20": "#2eb0ff",
  "22": "#c8e4ff",
  "23": "#ff88c8",
  "24": "#00d4ff",
  "25": "#5088ff",
  "27": "#b070ff",
  "28": "#30e0e0",
};

const CONSTELLATION_FALLBACK = [
  "#3db8ff",
  "#ff88c8",
  "#c8e4ff",
  "#00d4ff",
  "#ff70c0",
  "#5088ff",
  "#b070ff",
] as const;

/** 별자리 그래프용 — 카테고리 색을 밝은 별빛 톤으로 (범용 변환) */
export function constellationStarColor(hex: string, mix = 0.45): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return "#e8f0ff";
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  const r = parseInt(raw.slice(0, 2), 16);
  const g = parseInt(raw.slice(2, 4), 16);
  const b = parseInt(raw.slice(4, 6), 16);
  const nr = clamp(r * (1 - mix) + 235 * mix);
  const ng = clamp(g * (1 - mix) + 240 * mix);
  const nb = clamp(b * (1 - mix) + 255 * mix);
  return `#${[nr, ng, nb].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

export function constellationCategoryColorMap(categoryIds: string[]): Map<string, string> {
  const unique = [...new Set(categoryIds)].sort();
  const map = new Map<string, string>();
  let fallbackIdx = 0;
  for (const id of unique) {
    const fixed = CONSTELLATION_STAR_COLORS[id];
    if (fixed) {
      map.set(id, fixed);
    } else {
      map.set(id, CONSTELLATION_FALLBACK[fallbackIdx % CONSTELLATION_FALLBACK.length]);
      fallbackIdx += 1;
    }
  }
  return map;
}

export function hexToRgba(hex: string, alpha: number): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return `rgba(148, 163, 184, ${alpha})`;
  const r = parseInt(raw.slice(0, 2), 16);
  const g = parseInt(raw.slice(2, 4), 16);
  const b = parseInt(raw.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function categoryColorMap(categoryIds: string[]): Map<string, string> {
  const unique = [...new Set(categoryIds)].sort();
  const map = new Map<string, string>();
  let fallbackIdx = 0;
  for (const id of unique) {
    const fixed = CATEGORY_ID_COLORS[id];
    if (fixed) {
      map.set(id, fixed);
    } else {
      map.set(id, FALLBACK_PALETTE[fallbackIdx % FALLBACK_PALETTE.length]);
      fallbackIdx += 1;
    }
  }
  return map;
}

export interface CategoryRegion {
  id: string;
  label: string;
  color: string;
  cx: number;
  cy: number;
  radius: number;
  count: number;
}

interface Point2D {
  x: number;
  y: number;
  category_id: string;
}

/** 카테고리별 중심·반경 (PCA 좌표계) */
export function computeCategoryRegions(
  nodes: Point2D[],
  colors: Map<string, string>,
  labels: (id: string) => string,
  options?: { minCount?: number; maxRegions?: number },
): CategoryRegion[] {
  const minCount = options?.minCount ?? 10;
  const maxRegions = options?.maxRegions ?? 6;
  const byCat = new Map<string, Point2D[]>();

  for (const node of nodes) {
    const group = byCat.get(node.category_id) ?? [];
    group.push(node);
    byCat.set(node.category_id, group);
  }

  const regions: CategoryRegion[] = [];
  for (const [id, group] of byCat) {
    if (group.length < minCount) continue;
    const cx = group.reduce((sum, n) => sum + n.x, 0) / group.length;
    const cy = group.reduce((sum, n) => sum + n.y, 0) / group.length;
    const variance =
      group.reduce((sum, n) => {
        const dx = n.x - cx;
        const dy = n.y - cy;
        return sum + dx * dx + dy * dy;
      }, 0) / group.length;
    const radius = Math.max(0.12, Math.sqrt(variance) * 1.35);

    regions.push({
      id,
      label: labels(id),
      color: colors.get(id) ?? "#94a3b8",
      cx,
      cy,
      radius,
      count: group.length,
    });
  }

  return regions.sort((a, b) => b.count - a.count).slice(0, maxRegions);
}
