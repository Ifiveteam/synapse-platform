import { apiFetchAuth } from "@/api/client";

const PREFIX = "/api/v1/tracking";

export interface BehaviorLogItem {
  id: number;
  url: string;
  domain: string;
  page_title: string | null;
  duration_seconds: number;
  timestamp: string;
}

interface BehaviorLogListResponseDto {
  items: BehaviorLogItem[];
}

export interface DomainDurationStat {
  name: string;
  value: number;
  duration_seconds: number;
}

export interface TodayStats {
  total_duration_seconds: number;
  top_domains: DomainDurationStat[];
}

export async function fetchBehaviorEvents(
  limit = 50,
): Promise<BehaviorLogItem[]> {
  const res = await apiFetchAuth<BehaviorLogListResponseDto>(
    `${PREFIX}/events?limit=${limit}`,
  );
  return res.items;
}

export async function fetchTodayBehaviorStats(): Promise<TodayStats> {
  return apiFetchAuth<TodayStats>(`${PREFIX}/stats/today`);
}
