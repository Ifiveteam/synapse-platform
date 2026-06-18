import { apiFetch } from "@/api/client";
import type {
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

export function analyzeProfile(
  userId: string,
  email: string,
): Promise<AnalyzeResponse> {
  return apiFetch<AnalyzeResponse>(`${PROFILER_PREFIX}/analyze`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, email }),
  });
}

export function getJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`${PROFILER_PREFIX}/jobs/${jobId}`);
}

export function getProfile(userId: string): Promise<ProfilerResult> {
  return apiFetch<ProfilerResult>(`${PROFILER_PREFIX}/profile/${userId}`);
}

export function getGraph(
  userId: string,
  kind: "taste" | "knowledge",
): Promise<GraphViewData> {
  const params = new URLSearchParams({ kind });
  return apiFetch<GraphViewData>(
    `${PROFILER_PREFIX}/profile/${userId}/graph?${params}`,
  );
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
