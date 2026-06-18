import { apiFetchAuth } from "@/api/client";

export interface CatalogGraphSummary {
  total: number;
  categories: Array<{ category_id: string; count: number }>;
  channels: Array<{ channel: string; count: number; category_id: string }>;
}

export interface EmbeddingGraphNode {
  id: string;
  title: string;
  channel: string;
  category_id: string;
  is_shorts: boolean;
}

export interface EmbeddingGraphCluster {
  category_id: string;
  x: number;
  y: number;
  radius: number;
  count: number;
}

export interface EmbeddingGraphEdge {
  source: string;
  target: string;
  similarity: number;
}

export interface EmbeddingGraphData {
  total: number;
  method: string;
  layout?: string;
  min_similarity?: number;
  max_edges_per_node?: number;
  knn_k?: number;
  clusters?: EmbeddingGraphCluster[];
  nodes: EmbeddingGraphNode[];
  edges: EmbeddingGraphEdge[];
}

export async function fetchCatalogGraphSummary(): Promise<CatalogGraphSummary> {
  return apiFetchAuth<CatalogGraphSummary>("/api/v1/indexer/graph-summary");
}

export async function fetchEmbeddingGraph(): Promise<EmbeddingGraphData> {
  return apiFetchAuth<EmbeddingGraphData>("/api/v1/indexer/embedding-graph");
}
