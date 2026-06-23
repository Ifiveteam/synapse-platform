import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  MOCK_ACTIVE_IDEAL_LABEL,
  MOCK_CHATS,
  MOCK_SCRAPS,
  type SidebarChat,
  type SidebarScrap,
} from "@/lib/sidebar/mock";

interface SidebarStore {
  /** 현재 적용 중인 이상향 표시 라벨 (백엔드 active 이상향 기준) */
  activeIdealLabel: string | null;
  scraps: SidebarScrap[];
  chats: SidebarChat[];
  setActiveIdealLabel: (label: string | null) => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set) => ({
      activeIdealLabel: MOCK_ACTIVE_IDEAL_LABEL,
      scraps: MOCK_SCRAPS,
      chats: MOCK_CHATS,
      setActiveIdealLabel: (activeIdealLabel) => set({ activeIdealLabel }),
    }),
    {
      name: "synapse-sidebar",
      partialize: (s) => ({ activeIdealLabel: s.activeIdealLabel }),
    },
  ),
);
