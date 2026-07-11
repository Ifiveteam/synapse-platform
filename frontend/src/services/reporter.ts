import axios from "axios";

import { API_BASE_URL } from "@/lib/env";

/** react-force-graph 노드 — 백엔드 graph_data.nodes 항목 */
export interface KnowledgeGraphNode {
  id: string;
  group: string;
  val: number;
}

/** react-force-graph 링크 — 백엔드 graph_data.links 항목 */
export type KnowledgeGraphLinkType =
  | "cooccurrence"
  | "semantic"
  | "domain_hub";

export interface KnowledgeGraphLink {
  source: string;
  target: string;
  value: number;
  link_type?: KnowledgeGraphLinkType;
  similarity?: number;
}

/** 지식 그래프 API 응답 본문 */
export interface KnowledgeGraphData {
  nodes: KnowledgeGraphNode[];
  links: KnowledgeGraphLink[];
  start_date?: string | null;
  end_date?: string | null;
  snapshot_count?: number | null;
}

export interface MarkdownReportData {
  markdown: string;
  source: "file" | "db" | "fallback" | string;
}

export interface StreamSeriesPoint {
  date: string;
  axes: Record<string, number>;
  domains: Record<string, number>;
}

export interface StreamChartData {
  start_date: string;
  end_date: string;
  series: StreamSeriesPoint[];
}

export interface HeatmapData {
  days: number;
  day_labels: string[];
  matrix: number[][];
  max_count: number;
}

export interface PipelineRunResult {
  status: string;
  message: string;
  target_date: string;
}

export interface SnapshotInventoryDay {
  date: string;
  present: boolean;
  snapshot_id: string | null;
  created_at: string | null;
  keyword_count: number;
  top_keywords: string[];
  domain_keys: string[];
}

export interface SnapshotInventory {
  start_date: string;
  end_date: string;
  present_count: number;
  missing_count: number;
  days: SnapshotInventoryDay[];
}

export interface SnapshotKeywordRow {
  keyword: string;
  score: number;
  count_today: number;
  rank: number;
}

export interface SnapshotDomainRow {
  domain: string;
  user_count: number;
  total_duration: number;
  avg_weight: number;
}

export interface SnapshotSemanticLinkRow {
  source: string;
  target: string;
  similarity: number;
  link_type: string;
}

export interface SnapshotDetail {
  date: string;
  present: boolean;
  snapshot_id: string | null;
  snapshot_date: string | null;
  created_at: string | null;
  keywords: SnapshotKeywordRow[];
  domains: SnapshotDomainRow[];
  axes: Record<string, number>;
  semantic_link_count: number;
  semantic_links: SnapshotSemanticLinkRow[];
  external_keywords: string[];
  scrap_categories: string[];
  context_count: number;
  has_cross_domain_insights: boolean;
  report_source: string | null;
  report_preview: string | null;
  day_graph_nodes: number | null;
  day_graph_links: number | null;
}

const reporterClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

/** KST 기준 오늘 날짜 (YYYY-MM-DD) */
export function todayKstDateString(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(
    new Date(),
  );
}

export function shiftKstDateString(base: string, deltaDays: number): string {
  const [year, month, day] = base.split("-").map(Number);
  const utc = Date.UTC(year, month - 1, day);
  const shifted = new Date(utc + deltaDays * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(
    shifted,
  );
}

/** 종료일 기준 N일(기본 14일) 스냅샷을 롤업한 지식 그래프를 조회한다. */
export async function fetchKnowledgeGraph(
  endDate: string,
  days: number = 14,
): Promise<KnowledgeGraphData> {
  const { data } = await reporterClient.get<KnowledgeGraphData>(
    "/api/v1/reporter/graph",
    { params: { date: endDate, days } },
  );
  return {
    nodes: Array.isArray(data.nodes) ? data.nodes : [],
    links: Array.isArray(data.links) ? data.links : [],
    start_date: data.start_date ?? null,
    end_date: data.end_date ?? endDate,
    snapshot_count: data.snapshot_count ?? 0,
  };
}

/** 일별 B2B 마크다운 리포트를 조회한다. */
export async function fetchMarkdownReport(
  date: string,
): Promise<MarkdownReportData> {
  const { data } = await reporterClient.get<MarkdownReportData>(
    "/api/v1/reporter/report",
    { params: { date } },
  );
  return {
    markdown: typeof data.markdown === "string" ? data.markdown : "",
    source: data.source ?? "fallback",
  };
}

/** 8축·도메인 시계열 스트림 데이터를 조회한다. */
export async function fetchStreamGraphData(
  endDate: string,
  rangeDays: 7 | 30 = 7,
): Promise<StreamChartData> {
  const startDate = shiftKstDateString(endDate, -(rangeDays - 1));
  const { data } = await reporterClient.get<StreamChartData>(
    "/api/v1/reporter/charts/stream",
    { params: { start_date: startDate, end_date: endDate } },
  );
  return {
    start_date: data.start_date ?? startDate,
    end_date: data.end_date ?? endDate,
    series: Array.isArray(data.series) ? data.series : [],
  };
}

/** 온디맨드 — 선택 일자의 Reporter 일별 파이프라인을 즉시 실행한다. */
export async function triggerDailyPipeline(
  dateString: string,
): Promise<PipelineRunResult> {
  const { data } = await reporterClient.post<PipelineRunResult>(
    "/api/v1/reporter/run-pipeline",
    null,
    { params: { date_str: dateString } },
  );
  return {
    status: data.status ?? "success",
    message: data.message ?? "파이프라인이 완료되었습니다.",
    target_date: data.target_date ?? dateString,
  };
}

/** 관리자 — 기간 내 일별 스냅샷 인벤토리를 조회한다. */
export async function fetchSnapshotInventory(
  endDate: string,
  days: number = 30,
): Promise<SnapshotInventory> {
  const { data } = await reporterClient.get<SnapshotInventory>(
    "/api/v1/reporter/snapshots",
    { params: { date: endDate, days } },
  );
  return {
    start_date: data.start_date ?? endDate,
    end_date: data.end_date ?? endDate,
    present_count: data.present_count ?? 0,
    missing_count: data.missing_count ?? 0,
    days: Array.isArray(data.days) ? data.days : [],
  };
}

/** 관리자 — 단일 일자 스냅샷·리포트·당일 그래프 상세를 조회한다. */
export async function fetchSnapshotDetail(
  dateString: string,
): Promise<SnapshotDetail> {
  const { data } = await reporterClient.get<SnapshotDetail>(
    "/api/v1/reporter/snapshots/detail",
    { params: { date: dateString } },
  );
  return {
    date: data.date ?? dateString,
    present: Boolean(data.present),
    snapshot_id: data.snapshot_id ?? null,
    snapshot_date: data.snapshot_date ?? null,
    created_at: data.created_at ?? null,
    keywords: Array.isArray(data.keywords) ? data.keywords : [],
    domains: Array.isArray(data.domains) ? data.domains : [],
    axes: data.axes && typeof data.axes === "object" ? data.axes : {},
    semantic_link_count: data.semantic_link_count ?? 0,
    semantic_links: Array.isArray(data.semantic_links)
      ? data.semantic_links
      : [],
    external_keywords: Array.isArray(data.external_keywords)
      ? data.external_keywords
      : [],
    scrap_categories: Array.isArray(data.scrap_categories)
      ? data.scrap_categories
      : [],
    context_count: data.context_count ?? 0,
    has_cross_domain_insights: Boolean(data.has_cross_domain_insights),
    report_source: data.report_source ?? null,
    report_preview: data.report_preview ?? null,
    day_graph_nodes: data.day_graph_nodes ?? null,
    day_graph_links: data.day_graph_links ?? null,
  };
}

/** 최근 7일 활동 히트맵 매트릭스를 조회한다. */
export async function fetchHeatmapData(): Promise<HeatmapData> {
  const { data } = await reporterClient.get<HeatmapData>(
    "/api/v1/reporter/charts/heatmap",
  );
  return {
    days: data.days ?? 7,
    day_labels: Array.isArray(data.day_labels)
      ? data.day_labels
      : ["월", "화", "수", "목", "금", "토", "일"],
    matrix: Array.isArray(data.matrix) ? data.matrix : [],
    max_count: data.max_count ?? 0,
  };
}
