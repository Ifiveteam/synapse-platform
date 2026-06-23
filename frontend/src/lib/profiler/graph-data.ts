import type {
  GraphEdge,
  GraphViewData,
  SynapseAxisKey,
} from "@/api/types/profiler";

export interface ForceGraphNode {
  id: string;
  name: string;
  type: string;
  weight: number;
  val: number;
  x?: number;
  y?: number;
}

export interface ForceGraphLink {
  source: string;
  target: string;
  weight: number;
  relation: string;
  directed?: boolean;
}

export interface ForceGraphData {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
}

function undirectedPair(source: string, target: string): [string, string] {
  return source <= target ? [source, target] : [target, source];
}

/** Merge duplicate undirected edges (same pair + relation). */
function mergeUndirectedEdges(edges: GraphEdge[]): GraphEdge[] {
  const merged = new Map<string, GraphEdge>();
  for (const edge of edges) {
    const [source, target] = undirectedPair(edge.source, edge.target);
    const key = `${source}|${target}|${edge.relation}`;
    const existing = merged.get(key);
    if (existing) {
      existing.weight += edge.weight;
    } else {
      merged.set(key, {
        source,
        target,
        weight: edge.weight,
        relation: edge.relation,
        directed: false,
      });
    }
  }
  return Array.from(merged.values());
}

const NODE_COLORS: Record<string, string> = {
  tag: "#7dd3fc",
  channel: "#6ee7b7",
  axis: "#e9d5ff",
  domain: "#fdba74",
};

const AXIS_COLORS: Record<SynapseAxisKey, string> = {
  intellectual_curiosity: "#a78bfa",
  practical_orientation: "#38bdf8",
  emotional_comfort: "#f9a8d4",
  social_awareness: "#fbbf24",
  creative_expression: "#fb923c",
  entertainment_release: "#4ade80",
  self_improvement: "#22d3ee",
  depth_immersion: "#c084fc",
};

export function nodeColor(type: string, nodeId?: string): string {
  if (type === "axis" && nodeId?.startsWith("axis:")) {
    const key = nodeId.slice(5) as SynapseAxisKey;
    return AXIS_COLORS[key] ?? NODE_COLORS.axis;
  }
  return NODE_COLORS[type] ?? "#94a3b8";
}

export function toForceGraphData(
  graph: GraphViewData,
  maxNodes = 40,
  maxLinks = 100,
): ForceGraphData {
  const sortedNodes = graph.nodes
    .slice()
    .sort((a, b) => b.weight - a.weight)
    .slice(0, maxNodes);
  const nodeIds = new Set(sortedNodes.map((node) => node.id));
  const maxWeight = Math.max(...sortedNodes.map((node) => node.weight), 1);

  const nodes: ForceGraphNode[] = sortedNodes.map((node) => ({
    id: node.id,
    name: node.label,
    type: node.type,
    weight: node.weight,
    val: Math.max(3, (node.weight / maxWeight) * 12),
  }));

  const links: ForceGraphLink[] = mergeUndirectedEdges(
    graph.edges.filter(
      (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target),
    ),
  )
    .sort((a, b) => b.weight - a.weight)
    .slice(0, maxLinks)
    .map((edge) => ({
      source: edge.source,
      target: edge.target,
      weight: edge.weight,
      relation: edge.relation,
      directed: false,
    }));

  return { nodes, links };
}

export function buildGraphData(graph: GraphViewData): ForceGraphData {
  if (graph.kind === "taste") {
    return toForceGraphData(graph, 36, 90);
  }
  return toForceGraphData(graph, 28, 60);
}

export function neighborIds(
  nodeId: string,
  links: Array<{ source: string | ForceGraphNode; target: string | ForceGraphNode }>,
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

export function formatNodeType(type: string): string {
  const labels: Record<string, string> = {
    tag: "태그",
    channel: "채널",
    axis: "Synapse 축",
    domain: "도메인",
  };
  return labels[type] ?? type;
}

export function linkColor(relation: string, active: boolean): string {
  if (!active) return "rgba(51,65,85,0.2)";
  switch (relation) {
    case "maps_to":
      return "rgba(196,181,253,0.9)";
    case "watch":
      return "rgba(110,231,183,0.75)";
    case "related":
      return "rgba(251,191,36,0.8)";
    case "co_occur":
    case "same_content":
      return "rgba(125,211,252,0.5)";
    default:
      return "rgba(148,163,184,0.5)";
  }
}
