// ──────────────────────────────────────────
// Navigator API Client — v1.1
// ──────────────────────────────────────────

import type {
  ProfilerData,
  IdealRadarChart,
  IdealType,
  Guide,
  Quest,
} from "./types";
import type { DbProfileResponse } from "@/api/types/profiler";
import { API_BASE_URL } from "@/lib/env";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ──────────────────────────────────────────
// 응답 타입
// ──────────────────────────────────────────

export interface IdealDesignResponse {
  user_id:       string;
  proposals:     IdealRadarChart[];
  agent_message: string;
}

export interface ConfirmIdealResponse {
  guide:   Guide;
  quests:  Quest[];
  message: string;
}

export interface DirectModifyResponse {
  updated_ideal: IdealRadarChart;
  suggestions:   string[];
}

export interface ChatModifyResponse {
  updated_ideal: IdealRadarChart;
  adjustments:   { axis: string; delta: number; reason: string }[];
  reasoning:     string;
  reply:         string;
}

export interface AutoOptimalResponse {
  ideal:     IdealRadarChart;
  reasoning: string;
}

// ──────────────────────────────────────────
// API 함수
// ──────────────────────────────────────────

/** 수식 기반 이상향 3종 자동 생성 */
export async function designIdeal(
  profilerData: ProfilerData,
  top5Interests: string[],
): Promise<IdealDesignResponse> {
  return apiFetch<IdealDesignResponse>("/navigator/design", {
    method: "POST",
    body: JSON.stringify({
      user_id:        profilerData.user_id,
      profiler_data:  profilerData,
      top5_interests: top5Interests,
    }),
  });
}

/** 이상향 확정 → 가이드 + 퀘스트 생성 */
export async function confirmIdeal(
  profilerData: ProfilerData,
  selectedIdeal: IdealRadarChart,
  top5Interests: string[],
): Promise<ConfirmIdealResponse> {
  return apiFetch<ConfirmIdealResponse>("/navigator/confirm", {
    method: "POST",
    body: JSON.stringify({
      user_id:        profilerData.user_id,
      profiler_data:  profilerData,
      selected_ideal: selectedIdeal,
      top5_interests: top5Interests,
    }),
  });
}

/** Mode 1: 직접 수치 수정 */
export async function modifyDirect(
  userId: string,
  ideal: IdealRadarChart,
  axis: string,
  newValue: number,
): Promise<DirectModifyResponse> {
  return apiFetch<DirectModifyResponse>("/navigator/ideal/direct", {
    method: "PATCH",
    body: JSON.stringify({
      user_id:   userId,
      ideal,
      axis,
      new_value: newValue,
    }),
  });
}

/** Mode 2: 자연어 대화 수정 */
export async function modifyByChat(
  userId: string,
  ideal: IdealRadarChart,
  userMessage: string,
  profilerData?: ProfilerData,
): Promise<ChatModifyResponse> {
  return apiFetch<ChatModifyResponse>("/navigator/ideal/chat", {
    method: "POST",
    body: JSON.stringify({
      user_id:       userId,
      ideal,
      user_message:  userMessage,
      profiler_data: profilerData ?? null,
    }),
  });
}

/** Mode 3: AI 최적 이상향 설계 */
export async function optimizeAuto(
  profilerData: ProfilerData,
  top5Interests: string[],
  userGoal?: string,
): Promise<AutoOptimalResponse> {
  return apiFetch<AutoOptimalResponse>("/navigator/ideal/auto", {
    method: "POST",
    body: JSON.stringify({
      user_id:        profilerData.user_id,
      profiler_data:  profilerData,
      top5_interests: top5Interests,
      user_goal:      userGoal ?? null,
    }),
  });
}

// ──────────────────────────────────────────
// SSE 스트리밍 채팅
// ──────────────────────────────────────────

export interface ChatStreamOptions {
  profilerData:      ProfilerData;
  top5Interests:     string[];
  userMessage:       string;
  selectedIdeal?:    IdealRadarChart;
  isIdealConfirmed?: boolean;
  onChunk:           (text: string) => void;
  onDone:            () => void;
  onError:           (err: string) => void;
}

export async function streamChat(options: ChatStreamOptions): Promise<void> {
  const {
    profilerData, top5Interests, userMessage,
    selectedIdeal, isIdealConfirmed,
    onChunk, onDone, onError,
  } = options;

  const res = await fetch(`${API_BASE_URL}/api/v1/navigator/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id:            profilerData.user_id,
      profiler_data:      profilerData,
      top5_interests:     top5Interests,
      user_message:       userMessage,
      selected_ideal:     selectedIdeal ?? null,
      is_ideal_confirmed: isIdealConfirmed ?? false,
    }),
  });

  if (!res.ok || !res.body) {
    onError(`API error ${res.status}`);
    return;
  }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    for (const line of text.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[DONE]") { onDone(); return; }
      if (data.startsWith("[ERROR]")) { onError(data.slice(8)); return; }
      onChunk(data);
    }
  }
  onDone();
}

// ──────────────────────────────────────────
// Profiler 결과 → Navigator 입력 변환 헬퍼
// ──────────────────────────────────────────

/**
 * Profiler Agent 결과를 Navigator Agent 입력 형식으로 변환합니다.
 *
 * - axes      → layer_a  (필드명만 다름, 값은 동일)
 * - layer_b   → layer_b  (필드명 동일)
 * - top5_interests: Top5Interest[] → string[]  (label만 추출)
 */
export function toProfilerData(result: DbProfileResponse): ProfilerData {
  // 신형 DbProfileResponse(scores/top_categories) → Navigator ProfilerData 매핑.
  // scores에 8축 키가 있으면 사용, 없으면 0. layer_b는 DbProfileResponse에
  // 대응 데이터가 없어 0으로 둠(백엔드 보강 시 연동 — 후속 과제).
  const scores = result.scores ?? {};
  const axis = (k: string) => scores[k] ?? 0;
  return {
    user_id:     result.user_id,
    computed_at: result.snapshot_date,
    layer_a: {
      user_id:                result.user_id,
      intellectual_curiosity: axis("intellectual_curiosity"),
      self_improvement:       axis("self_improvement"),
      social_awareness:       axis("social_awareness"),
      depth_immersion:        axis("depth_immersion"),
      practical_orientation:  axis("practical_orientation"),
      emotional_comfort:      axis("emotional_comfort"),
      creative_expression:    axis("creative_expression"),
      entertainment_release:  axis("entertainment_release"),
    },
    layer_b: {
      search_active_ratio:   0,
      viewing_concentration: 0,
      taste_diversity_index: 0,
      exploration_depth:     0,
    },
    top5_interests: (result.top_categories ?? []).slice(0, 5).map((c) => c.category_id),
    summary:        result.summary_text ?? "",
  };
}

// ──────────────────────────────────────────
// 이상향 타입 → IdealRadarChart 변환 헬퍼
// ──────────────────────────────────────────

export function findIdealByType(
  proposals: IdealRadarChart[],
  type: IdealType,
): IdealRadarChart | undefined {
  return proposals.find((p) => p.ideal_type === type);
}
