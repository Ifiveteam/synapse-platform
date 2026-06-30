import type { ScrapGraphData, ScrapGraphNode } from "@/api/scraps";
import { scrapCategoryColorMap } from "@/lib/scraps/category-colors";

export interface ScrapForceNode {
  id: string;
  name: string;
  val: number;
  color: string;
  category: string;
  tags: string[];
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
  ox?: number;
  oy?: number;
}

export interface ScrapForceLink {
  source: string;
  target: string;
  similarity: number;
}

export interface ToScrapForceGraphOptions {
  minSimilarity: number;
}

export function toScrapForceGraph(
  data: ScrapGraphData,
  options: ToScrapForceGraphOptions,
): { nodes: ScrapForceNode[]; links: ScrapForceLink[] } {
  const colors = scrapCategoryColorMap(data.nodes.map((n) => n.category));
  const nodes: ScrapForceNode[] = data.nodes.map((node) =>
    nodeToForce(node, colors.get(node.category) ?? "#3db8ff"),
  );

  const ids = new Set(nodes.map((n) => n.id));
  const links = data.links
    .filter(
      (link) =>
        link.similarity >= options.minSimilarity &&
        ids.has(link.source) &&
        ids.has(link.target),
    )
    .map((link) => ({
      source: link.source,
      target: link.target,
      similarity: link.similarity,
    }));

  return { nodes, links };
}

function nodeToForce(node: ScrapGraphNode, color: string): ScrapForceNode {
  const title = node.title?.trim() || "(제목 없음)";
  return {
    id: node.id,
    name: title.length > 28 ? `${title.slice(0, 27)}…` : title,
    val: 7,
    color,
    category: node.category,
    tags: node.tags ?? [],
  };
}

export function neighborIdSet(
  nodeId: string,
  links: Array<{ source: string | ScrapForceNode; target: string | ScrapForceNode }>,
): Set<string> {
  const ids = new Set<string>([nodeId]);
  for (const link of links) {
    const source = typeof link.source === "object" ? link.source.id : link.source;
    const target = typeof link.target === "object" ? link.target.id : link.target;
    if (source === nodeId) ids.add(target);
    if (target === nodeId) ids.add(source);
  }
  return ids;
}

export interface NeighborBySimilarity {
  id: string;
  similarity: number;
}

function linkEndpointId(endpoint: string | ScrapForceNode): string {
  return typeof endpoint === "object" ? endpoint.id : endpoint;
}

export function sortedNeighborsBySimilarity(
  nodeId: string,
  links: Array<{
    source: string | ScrapForceNode;
    target: string | ScrapForceNode;
    similarity: number;
  }>,
): NeighborBySimilarity[] {
  const neighbors: NeighborBySimilarity[] = [];
  for (const link of links) {
    const source = linkEndpointId(link.source);
    const target = linkEndpointId(link.target);
    if (source === nodeId) {
      neighbors.push({ id: target, similarity: link.similarity });
    } else if (target === nodeId) {
      neighbors.push({ id: source, similarity: link.similarity });
    }
  }
  return neighbors.sort((a, b) => b.similarity - a.similarity);
}

export function collectScrapFilterOptions(items: ScrapGraphNode[]): {
  categories: Array<{ label: string; count: number }>;
  tags: Array<{ label: string; count: number }>;
} {
  const categoryCounts = new Map<string, number>();
  const tagCounts = new Map<string, number>();

  for (const node of items) {
    const category = node.category.trim();
    if (category) {
      categoryCounts.set(category, (categoryCounts.get(category) ?? 0) + 1);
    }
    for (const tag of node.tags ?? []) {
      const normalized = tag.trim();
      if (!normalized) continue;
      tagCounts.set(normalized, (tagCounts.get(normalized) ?? 0) + 1);
    }
  }

  const categories = [...categoryCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({ label, count }));

  const tags = [...tagCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({ label, count }));

  return { categories, tags };
}
