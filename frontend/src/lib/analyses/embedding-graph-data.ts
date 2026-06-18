import type { EmbeddingGraphData, EmbeddingGraphNode } from "@/api/indexer";
import { constellationCategoryColorMap } from "@/lib/analyses/category-colors";

export interface CatalogForceNode {
  id: string;
  name: string;
  val: number;
  color: string;
  categoryId: string;
  channel: string;
  isShorts: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
  ox?: number;
  oy?: number;
}

export interface CatalogForceLink {
  source: string;
  target: string;
  similarity: number;
}

export function toCatalogForceGraph(
  data: EmbeddingGraphData,
  categoryFilter: string | null,
): { nodes: CatalogForceNode[]; links: CatalogForceLink[] } {
  const colors = constellationCategoryColorMap(data.nodes.map((n) => n.category_id));
  const minSimilarity = data.min_similarity ?? 0.6;
  const nodes: CatalogForceNode[] = data.nodes
    .filter((n) => !categoryFilter || n.category_id === categoryFilter)
    .map((n) =>
      nodeToForce(n, colors.get(n.category_id) ?? "#3db8ff"),
    );

  const ids = new Set(nodes.map((n) => n.id));
  const links = data.edges
    .filter(
      (e) =>
        e.similarity >= minSimilarity && ids.has(e.source) && ids.has(e.target),
    )
    .map((e) => ({
      source: e.source,
      target: e.target,
      similarity: e.similarity,
    }));

  return { nodes, links };
}

/** force 시뮬레이션 변형 방지 — 2D/3D 각각 독립 복사본 사용 */
export function cloneCatalogForceGraph(graph: {
  nodes: CatalogForceNode[];
  links: Array<{
    source: string | CatalogForceNode;
    target: string | CatalogForceNode;
    similarity: number;
  }>;
}): { nodes: CatalogForceNode[]; links: CatalogForceLink[] } {
  return {
    nodes: graph.nodes.map((node) => ({ ...node })),
    links: graph.links.map((link) => ({
      source: typeof link.source === "object" ? link.source.id : link.source,
      target: typeof link.target === "object" ? link.target.id : link.target,
      similarity: link.similarity,
    })),
  };
}

function nodeToForce(node: EmbeddingGraphNode, color: string): CatalogForceNode {
  const title = node.title?.trim() || "(제목 없음)";
  return {
    id: node.id,
    name: title.length > 28 ? `${title.slice(0, 27)}…` : title,
    val: node.is_shorts ? 5 : 7,
    color,
    categoryId: node.category_id,
    channel: node.channel,
    isShorts: node.is_shorts,
  };
}

export function neighborIdSet(
  nodeId: string,
  links: Array<{ source: string | CatalogForceNode; target: string | CatalogForceNode }>,
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

function linkEndpointId(endpoint: string | CatalogForceNode): string {
  return typeof endpoint === "object" ? endpoint.id : endpoint;
}

export function sortedNeighborsBySimilarity(
  nodeId: string,
  links: Array<{
    source: string | CatalogForceNode;
    target: string | CatalogForceNode;
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
