import { create } from "zustand";
import { persist } from "zustand/middleware";

import { fetchArchiverSessions } from "@/api/archiver";
import { fetchCuratorSessions } from "@/api/curator";
import { fetchScraps } from "@/api/scraps";
import { buildSidebarScraps } from "@/lib/sidebar/build-sidebar-scraps";
import {
  MOCK_ACTIVE_IDEAL_LABEL,
  type SidebarChat,
  type SidebarScrap,
} from "@/lib/sidebar/mock";

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 60) return min <= 1 ? "방금 전" : `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const day = Math.floor(hr / 24);
  if (day === 1) return "어제";
  if (day < 7) return `${day}일 전`;
  return `${Math.floor(day / 7)}주 전`;
}

interface SidebarStore {
  /** 현재 적용 중인 이상향 표시 라벨 (백엔드 active 이상향 기준) */
  activeIdealLabel: string | null;
  scraps: SidebarScrap[];
  chats: SidebarChat[];
  setActiveIdealLabel: (label: string | null) => void;
  loadChats: () => Promise<void>;
  loadScraps: () => Promise<void>;
  renameChat: (id: string, title: string) => void;
  deleteChat: (id: string) => void;
  clearChats: () => void;
  clearScraps: () => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set) => ({
      activeIdealLabel: MOCK_ACTIVE_IDEAL_LABEL,
      scraps: [],
      chats: [],
      setActiveIdealLabel: (activeIdealLabel) => set({ activeIdealLabel }),
      renameChat: (id, title) =>
        set((s) => ({ chats: s.chats.map((c) => (c.id === id ? { ...c, title } : c)) })),

      deleteChat: (id) =>
        set((s) => ({ chats: s.chats.filter((c) => c.id !== id) })),

      clearChats: () => set({ chats: [] }),
      clearScraps: () => set({ scraps: [] }),

      loadChats: async () => {
        try {
          const sessions = await fetchCuratorSessions();
          set({
            chats: sessions.map((s) => ({
              id: s.session_id,
              title: s.title.length > 40 ? s.title.slice(0, 40) + "…" : s.title,
              updatedAt: formatRelativeTime(s.updated_at),
            })),
          });
        } catch {
          // 로그인 안 된 상태 등 무시
        }
      },

      loadScraps: async () => {
        try {
          const [scraps, sessions] = await Promise.all([
            fetchScraps(),
            fetchArchiverSessions(),
          ]);
          set({
            scraps: buildSidebarScraps(scraps, sessions, formatRelativeTime),
          });
        } catch {
          set({ scraps: [] });
        }
      },
    }),
    {
      name: "synapse-sidebar",
      partialize: (s) => ({
        activeIdealLabel: s.activeIdealLabel,
        chats: s.chats,
      }),
    },
  ),
);
