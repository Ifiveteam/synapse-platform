export type AnalysisStatus = "completed" | "pending" | "running";

export interface AnalysisResultItem {
  id: string;
  title: string;
  date: string;
  snapshotAt: string | null;
  status: AnalysisStatus;
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
