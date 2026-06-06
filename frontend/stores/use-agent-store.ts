import { create } from "zustand";

import type { AgentId } from "@/lib/agents";

interface AgentStore {
  selectedAgentId: AgentId | null;
  setSelectedAgentId: (id: AgentId | null) => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),
}));
