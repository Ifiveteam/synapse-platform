import { apiFetchAuth } from "@/api/client";
import type { AnalysisCompareResponse, DbProfileResponse } from "@/api/types/profiler";
import {
  formatAnalysisDate,
  type AnalysisResultItem,
  type AnalysisStage,
  type AnalysisStatus,
} from "@/lib/analyses/types";

const PREFIX = "/api/v1/profiler";

interface AnalysisListItemDto {
  id: string;
  title: string;
  file_name?: string | null;
  snapshot_date: string | null;
  status: AnalysisStatus;
  stage?: AnalysisStage | null;
  kind: "snapshot" | "job";
  batch_id?: string | null;
}

interface AnalysisListResponseDto {
  items: AnalysisListItemDto[];
}

function mapListItem(dto: AnalysisListItemDto): AnalysisResultItem {
  return {
    id: dto.id,
    title: dto.title,
    fileName: dto.file_name ?? null,
    date: formatAnalysisDate(dto.snapshot_date ?? undefined),
    snapshotAt: dto.snapshot_date,
    status: dto.status,
    stage: dto.stage ?? null,
    kind: dto.kind,
    batchId: dto.batch_id ?? null,
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

export async function fetchAnalysisCompare(
  fromId: string,
  toId: string,
): Promise<AnalysisCompareResponse> {
  const params = new URLSearchParams({ from: fromId, to: toId });
  return apiFetchAuth(`${PREFIX}/me/analyses/compare?${params.toString()}`);
}

import { youtubeCategoryLabel } from "@/lib/youtube-categories";

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

export interface TopCategoryItem {
  label: string;
  count: number;
}

/** API top_categories → 표시용 라벨 */
export function mapTopCategories(
  items: { category_id: string; count: number }[] | undefined,
): TopCategoryItem[] {
  if (!items?.length) return [];
  return items.map((item) => ({
    label: youtubeCategoryLabel(item.category_id),
    count: item.count,
  }));
}
