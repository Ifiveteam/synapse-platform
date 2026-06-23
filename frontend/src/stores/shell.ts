import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { AgentId } from "@/lib/agents";

interface ShellStore {
  sidebarExpanded: boolean;
  loginModalOpen: boolean;
  toggleSidebar: () => void;
  setSidebarExpanded: (expanded: boolean) => void;
  openLoginModal: () => void;
  closeLoginModal: () => void;
}

interface AgentSelectionStore {
  selectedAgentId: AgentId | null;
  setSelectedAgentId: (id: AgentId | null) => void;
}

export const useShellStore = create<ShellStore>()(
  persist(
    (set) => ({
      sidebarExpanded: true,
      loginModalOpen: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarExpanded: !s.sidebarExpanded })),
      setSidebarExpanded: (sidebarExpanded) => set({ sidebarExpanded }),
      openLoginModal: () => set({ loginModalOpen: true }),
      closeLoginModal: () => set({ loginModalOpen: false }),
    }),
    {
      name: "synapse-shell",
      partialize: (s) => ({ sidebarExpanded: s.sidebarExpanded }),
    },
  ),
);

export const useAgentSelection = create<AgentSelectionStore>()((set) => ({
  selectedAgentId: null,
  setSelectedAgentId: (selectedAgentId) => set({ selectedAgentId }),
}));
