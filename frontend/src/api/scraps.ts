import { apiFetchAuth } from "@/api/client";
import type { ArchiverChatMessage } from "@/api/archiver";

export interface ScrapGraphNode {
  id: string;
  title: string | null;
  category: string;
  tags: string[];
}

export interface ScrapGraphLink {
  source: string;
  target: string;
  similarity: number;
}

export interface ScrapGraphData {
  nodes: ScrapGraphNode[];
  links: ScrapGraphLink[];
}

export interface ScrapGraphQueryParams {
  categories?: string[];
  tags?: string[];
}

export interface ScrapItem {
  id: string;
  user_id: string;
  source_type: "web" | "chat";
  url: string | null;
  title: string | null;
  summary: string;
  category: string;
  tags: string[];
  raw_body_snapshot: string | null;
  session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScrapDetail {
  scrap: ScrapItem;
  archiver_session_id: string | null;
  archiver_history: ArchiverChatMessage[];
}

function buildGraphQuery(params?: ScrapGraphQueryParams): string {
  if (!params) return "";
  const qs = new URLSearchParams();
  if (params.categories?.length) {
    qs.set("categories", params.categories.join(","));
  }
  if (params.tags?.length) {
    qs.set("tags", params.tags.join(","));
  }
  const query = qs.toString();
  return query ? `?${query}` : "";
}

export async function fetchScrapGraph(
  params?: ScrapGraphQueryParams,
): Promise<ScrapGraphData> {
  return apiFetchAuth<ScrapGraphData>(
    `/api/v1/scraps/graph${buildGraphQuery(params)}`,
  );
}

export async function fetchScraps(): Promise<ScrapItem[]> {
  const res = await apiFetchAuth<{ status: string; data: ScrapItem[] }>(
    "/api/v1/scraps",
  );
  return res.data;
}

export async function fetchScrapDetail(scrapId: string): Promise<ScrapDetail> {
  const res = await apiFetchAuth<{ status: string; data: ScrapDetail }>(
    `/api/v1/scraps/${scrapId}`,
  );
  return res.data;
}
