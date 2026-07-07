import axios from "axios";

import { API_BASE_URL } from "@/lib/env";

const aggregatorClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export interface AggregatorTriggerResult {
  status: string;
  message: string;
}

/** 로컬 개발·시연용 — 어그리게이터 일별 배치 집계를 즉시 1회 트리거한다. */
export async function triggerAggregatorBatch(): Promise<AggregatorTriggerResult> {
  const { data } = await aggregatorClient.post<AggregatorTriggerResult>(
    "/api/v1/aggregator/trigger",
  );
  return {
    status: data.status ?? "success",
    message: data.message ?? "Aggregator batch job triggered manually",
  };
}
