import { TREND_API_BASE } from "@/lib/api/config";

export interface ProfileAxis {
  key: string;
  label: string;
  avg_score: number;
}

export interface AnalyzeResponse {
  post_id: string;
}

export interface TrendPostSummary {
  post_id: string;
  generated_at: string;
  cohort_size: number;
}

export interface TrendPostListResponse {
  items: TrendPostSummary[];
  total: number;
}

export interface TrendPostResponse {
  post_id: string;
  generated_at: string;
  cohort_size: number;
  axes: ProfileAxis[];
  report_markdown: string;
}

export async function fetchTrendPosts(): Promise<TrendPostListResponse> {
  const response = await fetch(`${TREND_API_BASE}/posts`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`게시글 목록을 불러오지 못했습니다. (${response.status})`);
  }

  return response.json() as Promise<TrendPostListResponse>;
}

export async function analyzeTrend(): Promise<AnalyzeResponse> {
  const response = await fetch(`${TREND_API_BASE}/analyze`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`트렌드 분석 요청에 실패했습니다. (${response.status})`);
  }

  return response.json() as Promise<AnalyzeResponse>;
}

export async function fetchTrendPost(postId: string): Promise<TrendPostResponse> {
  const response = await fetch(`${TREND_API_BASE}/posts/${postId}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`분석 게시글을 불러오지 못했습니다. (${response.status})`);
  }

  return response.json() as Promise<TrendPostResponse>;
}

export function getTrendPostPdfUrl(postId: string): string {
  return `${TREND_API_BASE}/posts/${postId}/download`;
}
