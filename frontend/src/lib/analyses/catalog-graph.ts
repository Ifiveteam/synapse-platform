import { youtubeCategoryLabel } from "@/lib/youtube-categories";

import type { CatalogGraphSummary } from "@/api/indexer";

export interface CatalogGraphNode {
  id: string;
  label: string;
  kind: "center" | "category" | "channel";
  count: number;
  cx: number;
  cy: number;
  r: number;
}

export interface CatalogGraphEdge {
  from: string;
  to: string;
}

export interface CatalogGraphLayout {
  nodes: CatalogGraphNode[];
  edges: CatalogGraphEdge[];
  total: number;
}

interface VideoLike {
  channel?: string | null;
  youtube_category_id?: string | null;
}

function polar(cx: number, cy: number, radius: number, angleRad: number) {
  return {
    cx: cx + radius * Math.cos(angleRad),
    cy: cy + radius * Math.sin(angleRad),
  };
}

function nodeRadius(count: number, maxCount: number, min: number, max: number) {
  if (maxCount <= 0) return min;
  const t = Math.sqrt(count / maxCount);
  return min + t * (max - min);
}

function buildLayoutFromAggregates(
  total: number,
  categories: Array<{ id: string; label: string; count: number }>,
  channels: Array<{ id: string; label: string; count: number; categoryId: string }>,
  options?: {
    centerLabel?: string;
    width?: number;
    height?: number;
  },
): CatalogGraphLayout {
  const width = options?.width ?? 720;
  const height = options?.height ?? 260;
  const centerX = width / 2;
  const centerY = height / 2;

  if (total <= 0 || categories.length === 0) {
    return { nodes: [], edges: [], total: 0 };
  }

  const catIds = new Set(categories.map((c) => c.id));
  const maxCatCount = categories[0]?.count ?? 1;
  const maxChCount = Math.max(...channels.map((c) => c.count), 1);

  const nodes: CatalogGraphNode[] = [
    {
      id: "center",
      label: options?.centerLabel ?? `${total}건`,
      kind: "center",
      count: total,
      cx: centerX,
      cy: centerY,
      r: 26,
    },
  ];
  const edges: CatalogGraphEdge[] = [];
  const catAngle = new Map<string, number>();

  categories.forEach((cat, index) => {
    const angle = -Math.PI / 2 + (index / categories.length) * Math.PI * 2;
    catAngle.set(cat.id, angle);
    const { cx, cy } = polar(centerX, centerY, 72, angle);
    const nodeId = `cat:${cat.id}`;
    nodes.push({
      id: nodeId,
      label: cat.label,
      kind: "category",
      count: cat.count,
      cx,
      cy,
      r: nodeRadius(cat.count, maxCatCount, 14, 22),
    });
    edges.push({ from: "center", to: nodeId });
  });

  const channelsByCat = new Map<string, typeof channels>();
  for (const ch of channels) {
    const bucket = catIds.has(ch.categoryId) ? ch.categoryId : categories[0]?.id ?? "unknown";
    if (!channelsByCat.has(bucket)) channelsByCat.set(bucket, []);
    channelsByCat.get(bucket)!.push(ch);
  }

  for (const [catId, chList] of channelsByCat) {
    const baseAngle = catAngle.get(catId) ?? 0;
    const spread = Math.min(0.55, 0.12 * chList.length);
    chList.forEach((ch, idx) => {
      const offset =
        chList.length === 1 ? 0 : -spread / 2 + (idx / (chList.length - 1)) * spread;
      const angle = baseAngle + offset;
      const { cx, cy } = polar(centerX, centerY, 118, angle);
      nodes.push({
        id: ch.id,
        label: ch.label,
        kind: "channel",
        count: ch.count,
        cx,
        cy,
        r: nodeRadius(ch.count, maxChCount, 10, 16),
      });
      const catNodeId = catIds.has(catId) ? `cat:${catId}` : "center";
      edges.push({ from: ch.id, to: catNodeId });
    });
  }

  return { nodes, edges, total };
}

/** API graph-summary → 레이아웃 */
export function buildCatalogGraphFromSummary(
  summary: CatalogGraphSummary,
  options?: { centerLabel?: string },
): CatalogGraphLayout {
  const categories = summary.categories.map((c) => ({
    id: c.category_id,
    label: youtubeCategoryLabel(c.category_id),
    count: c.count,
  }));
  const channels = summary.channels.map((c) => ({
    id: `ch:${c.channel}`,
    label: c.channel.length > 10 ? `${c.channel.slice(0, 9)}…` : c.channel,
    count: c.count,
    categoryId: c.category_id,
  }));

  return buildLayoutFromAggregates(summary.total, categories, channels, {
    centerLabel: options?.centerLabel ?? `${summary.total}건`,
  });
}

/** 프로필 스냅샷 top N 집계로 graph-summary 대체 */
export function graphSummaryFromProfile(
  topCategories: Array<{ category_id: string; count: number }>,
  topChannels: Array<{ channel: string; count: number }>,
): CatalogGraphSummary | null {
  if (!topCategories.length) return null;
  const total = topCategories.reduce((sum, item) => sum + item.count, 0);
  return {
    total,
    categories: topCategories,
    channels: topChannels.map((item) => ({
      channel: item.channel,
      count: item.count,
      category_id: topCategories[0]?.category_id ?? "unknown",
    })),
  };
}

function countBy<T extends string>(items: T[]): Map<T, number> {
  const map = new Map<T, number>();
  for (const item of items) {
    map.set(item, (map.get(item) ?? 0) + 1);
  }
  return map;
}

function topEntries(map: Map<string, number>, limit: number) {
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
}

/** catalog 영상 목록 → 레이아웃 (전체 fetch 시) */
export function buildCatalogGraphLayout(
  videos: VideoLike[],
  options?: {
    maxCategories?: number;
    maxChannels?: number;
    centerLabel?: string;
  },
): CatalogGraphLayout {
  const maxCategories = options?.maxCategories ?? 6;
  const maxChannels = options?.maxChannels ?? 8;

  if (videos.length === 0) {
    return { nodes: [], edges: [], total: 0 };
  }

  const categories = countBy(
    videos.map((v) => v.youtube_category_id?.trim() || "unknown"),
  );
  const channels = countBy(videos.map((v) => v.channel?.trim() || "unknown"));

  const topCats = topEntries(categories, maxCategories);
  const topChs = topEntries(channels, maxChannels);

  const channelPrimaryCat = new Map<string, string>();
  const channelCatCounts = new Map<string, Map<string, number>>();
  for (const video of videos) {
    const ch = video.channel?.trim() || "unknown";
    const cat = video.youtube_category_id?.trim() || "unknown";
    if (!channelCatCounts.has(ch)) channelCatCounts.set(ch, new Map());
    const inner = channelCatCounts.get(ch)!;
    inner.set(cat, (inner.get(cat) ?? 0) + 1);
  }
  for (const [ch, catMap] of channelCatCounts) {
    const primary = [...catMap.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "unknown";
    channelPrimaryCat.set(ch, primary);
  }

  const categoryRows = topCats.map(([id, count]) => ({
    id,
    label: youtubeCategoryLabel(id),
    count,
  }));
  const channelRows = topChs.map(([ch, count]) => ({
    id: `ch:${ch}`,
    label: ch.length > 10 ? `${ch.slice(0, 9)}…` : ch,
    count,
    categoryId: channelPrimaryCat.get(ch) ?? "unknown",
  }));

  return buildLayoutFromAggregates(videos.length, categoryRows, channelRows, {
    centerLabel: options?.centerLabel ?? `${videos.length}건`,
  });
}
