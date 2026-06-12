import { TREND_API_BASE } from "@/lib/api/config";

export interface CognitiveAxisScore {
  subject: string;
  key: string;
  score: number;
  interpretation: string;
}

export interface KeywordItem {
  rank: number;
  keyword: string;
  metrics: string;
  change: string;
}

export interface GapAnalysis {
  intersection_keywords: string[];
  intersection_interpretation: string;
  internal_only_keywords: string[];
  internal_only_interpretation: string;
  external_only_keywords: string[];
  external_only_interpretation: string;
  filter_bubble_scenario: string;
}

export interface B2BRecommendations {
  content_strategy: string[];
  marketing: string[];
  platform_policy: string[];
}

export interface DashboardReport {
  headline_summary: string;
  neutrality_score: number;
  neutrality_status: string;
  neutrality_reason: string;
  radar_chart_data: CognitiveAxisScore[];
  dominant_axes: string[];
  deficient_axes: string[];
  macro_trend_internal: KeywordItem[];
  macro_trend_external: KeywordItem[];
  gap_analysis: GapAnalysis;
  recommendations: B2BRecommendations;
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
  report: DashboardReport;
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

export async function analyzeTrend(email?: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${TREND_API_BASE}/analyze`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...(email ? { "Content-Type": "application/json" } : {}),
    },
    body: email ? JSON.stringify({ email }) : undefined,
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
