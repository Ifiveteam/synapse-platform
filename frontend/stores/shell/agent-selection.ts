import { create } from "zustand";

import type { AgentId } from "@/lib/agents";

/** 홈·에이전트 카드 등 플랫폼 셸에서만 쓰는 “현재 선택 에이전트” 상태 */
interface AgentSelectionStore {
  selectedAgentId: AgentId | null;
  setSelectedAgentId: (id: AgentId | null) => void;
}

export const useAgentSelection = create<AgentSelectionStore>((set) => ({
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),
}));
