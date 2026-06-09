/**
 * Profiler Agent 전역 상태
 *
 * - Profiler 분석 완료 시 결과를 저장
 * - Navigator 페이지에서 읽어 toProfilerData()로 변환 후 사용
 */

import { create } from "zustand";
import type { ProfilerResult } from "@/lib/types/profiler";

interface ProfilerStore {
  /** 가장 최근 분석 결과 (없으면 null) */
  result: ProfilerResult | null;
  /** 결과 저장 */
  setResult: (result: ProfilerResult) => void;
  /** 초기화 */
  clear: () => void;
}

export const useProfilerStore = create<ProfilerStore>((set) => ({
  result: null,
  setResult: (result) => set({ result }),
  clear: () => set({ result: null }),
}));
