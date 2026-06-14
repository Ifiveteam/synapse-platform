import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  MOCK_ACTIVE_IDEAL,
  MOCK_CHATS,
  MOCK_SCRAPS,
  type SidebarChat,
  type SidebarScrap,
} from "@/lib/sidebar/mock";
import type { IdealType } from "@/lib/navigator/types";

interface SidebarStore {
  activeIdealType: IdealType | null;
  scraps: SidebarScrap[];
  chats: SidebarChat[];
  setActiveIdealType: (type: IdealType | null) => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set) => ({
      activeIdealType: MOCK_ACTIVE_IDEAL,
      scraps: MOCK_SCRAPS,
      chats: MOCK_CHATS,
      setActiveIdealType: (activeIdealType) => set({ activeIdealType }),
    }),
    {
      name: "synapse-sidebar",
      partialize: (s) => ({ activeIdealType: s.activeIdealType }),
    },
  ),
);
