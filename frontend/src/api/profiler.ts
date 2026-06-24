import { apiFetch, apiFetchAuth } from "@/api/client";
import type {
  AnalysisListItem,
  AnalyzeResponse,
  GraphViewData,
  JobResponse,
  PersonasResponse,
  ProfilerResult,
} from "@/api/types/profiler";

const PROFILER_PREFIX = "/api/v1/profiler";

export function getPersonas(): Promise<PersonasResponse> {
  return apiFetch<PersonasResponse>(`${PROFILER_PREFIX}/personas`);
}

export function analyzeProfile(): Promise<AnalyzeResponse> {
  return apiFetchAuth<AnalyzeResponse>(`${PROFILER_PREFIX}/run`, {
    method: "POST",
  });
}

export function getJob(jobId: string): Promise<JobResponse> {
  return apiFetchAuth<JobResponse>(`${PROFILER_PREFIX}/jobs/${jobId}`);
}

export function getProfile(userId: string): Promise<ProfilerResult> {
  return apiFetch<ProfilerResult>(`${PROFILER_PREFIX}/profile/${userId}`);
}

export async function getGraph(kind: "taste" | "knowledge"): Promise<GraphViewData> {
  if (kind === "taste") {
    const raw = await apiFetchAuth<{
      total: number;
      categories: { category_id: string; count: number }[];
      channels: { channel: string; count: number; category_id: string }[];
    }>("/api/v1/indexer/graph-summary");

    const nodes: GraphViewData["nodes"] = [
      ...raw.categories.map((c) => ({
        id: `cat:${c.category_id}`,
        type: "category",
        label: c.category_id,
        weight: c.count,
      })),
      ...raw.channels.map((ch) => ({
        id: `ch:${ch.channel}`,
        type: "channel",
        label: ch.channel,
        weight: ch.count,
      })),
    ];
    const edges: GraphViewData["edges"] = raw.channels.map((ch) => ({
      source: `ch:${ch.channel}`,
      target: `cat:${ch.category_id}`,
      weight: ch.count,
      relation: "primary_category",
    }));
    return { kind: "taste", nodes, edges };
  }

  return apiFetchAuth<GraphViewData>("/api/v1/indexer/embedding-graph");
}

export function listMyAnalyses(): Promise<AnalysisListItem[]> {
  return apiFetchAuth<{ items: AnalysisListItem[] }>(`${PROFILER_PREFIX}/me/analyses`)
    .then((r) => r.items ?? [])
    .catch(() => []);
}

export async function pollJobUntilDone(
  jobId: string,
  options?: { intervalMs?: number; maxAttempts?: number },
): Promise<JobResponse> {
  const intervalMs = options?.intervalMs ?? 1500;
  const maxAttempts = options?.maxAttempts ?? 120;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const job = await getJob(jobId);
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error("분석 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.");
}
