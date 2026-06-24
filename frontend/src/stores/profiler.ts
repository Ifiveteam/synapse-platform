import { create } from "zustand";

import type { DbProfileResponse as ProfilerResult } from "@/api/types/profiler";

interface ProfilerStore {
  result: ProfilerResult | null;
  setResult: (result: ProfilerResult) => void;
  clear: () => void;
}

export const useProfilerStore = create<ProfilerStore>((set) => ({
  result: null,
  setResult: (result) => set({ result }),
  clear: () => set({ result: null }),
}));
