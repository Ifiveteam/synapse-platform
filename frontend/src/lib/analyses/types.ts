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
  /** 진행 중(job) 항목이 속한 배치 — 배치별 그룹핑에 사용 */
  batchId: string | null;
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
