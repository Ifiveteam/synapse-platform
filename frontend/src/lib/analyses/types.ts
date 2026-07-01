export type AnalysisStatus = "completed" | "pending" | "running";

/** running일 때 세부 단계 — indexing(분류) | indexed(분류완료) | profiling(분석) */
export type AnalysisStage = "indexing" | "indexed" | "profiling";

export interface AnalysisResultItem {
  id: string;
  title: string;
  fileName: string | null;
  date: string;
  snapshotAt: string | null;
  status: AnalysisStatus;
  stage: AnalysisStage | null;
  kind: "snapshot" | "job";
}

export const ANALYSIS_PAGE_SIZE = 5;

export function formatAnalysisDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}.${m}.${day}`;
}

export function isAnalysisPending(status: AnalysisStatus): boolean {
  return status === "pending" || status === "running";
}
