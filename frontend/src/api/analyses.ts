import { apiFetchAuth } from "@/api/client";
import type { DbProfileResponse } from "@/api/types/profiler";
import {
  formatAnalysisDate,
  type AnalysisResultItem,
  type AnalysisStatus,
} from "@/lib/analyses/types";

const PREFIX = "/api/v1/profiler";

interface AnalysisListItemDto {
  id: string;
  title: string;
  snapshot_date: string | null;
  status: AnalysisStatus;
  kind: "snapshot" | "job";
}

interface AnalysisListResponseDto {
  items: AnalysisListItemDto[];
}

function mapListItem(dto: AnalysisListItemDto): AnalysisResultItem {
  return {
    id: dto.id,
    title: dto.title,
    date: formatAnalysisDate(dto.snapshot_date ?? undefined),
    status: dto.status,
    kind: dto.kind,
  };
}

export async function fetchMyAnalyses(): Promise<AnalysisResultItem[]> {
  const res = await apiFetchAuth<AnalysisListResponseDto>(`${PREFIX}/me/analyses`);
  return res.items.map(mapListItem);
}

export async function fetchMyAnalysisSnapshot(
  snapshotId: string,
): Promise<DbProfileResponse> {
  return apiFetchAuth<DbProfileResponse>(`${PREFIX}/me/analyses/${snapshotId}`);
}

/** 행동 스파이더 8축 상위 5개 라벨 */
const BEHAVIOR_LABELS: Record<string, string> = {
  exploration: "탐색",
  analytical: "분석",
  creativity: "창의",
  execution: "실행",
  achievement_drive: "성취",
  autonomy: "자율",
  sociality: "사회성",
  sensitivity: "감수성",
};

export function topBehaviorKeywords(
  scores: Record<string, number>,
  limit = 5,
): string[] {
  const behaviorKeys = Object.keys(BEHAVIOR_LABELS);
  return Object.entries(scores)
    .filter(([key]) => behaviorKeys.includes(key))
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([key, value]) => `${BEHAVIOR_LABELS[key]} (${Math.round(value)})`);
}
