import type { ScrapForceNode } from "@/lib/scraps/scrap-graph-data";

export type ScrapHomeLayout = Map<string, { ox: number; oy: number }>;

export function captureScrapHomeLayout(nodes: ScrapForceNode[]): ScrapHomeLayout {
  const layout: ScrapHomeLayout = new Map();
  for (const node of nodes) {
    if (node.x != null && node.y != null) {
      layout.set(node.id, { ox: node.x, oy: node.y });
    }
  }
  return layout;
}

export function restoreScrapHomeLayout(
  nodes: ScrapForceNode[],
  layout: ScrapHomeLayout,
): boolean {
  if (layout.size === 0) return false;

  let restored = false;
  for (const node of nodes) {
    const home = layout.get(node.id);
    if (!home) continue;
    node.x = home.ox;
    node.y = home.oy;
    node.vx = 0;
    node.vy = 0;
    node.fx = undefined;
    node.fy = undefined;
    restored = true;
  }
  return restored;
}
