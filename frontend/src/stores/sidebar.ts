import { create } from "zustand";
import { persist } from "zustand/middleware";

import { fetchArchiverSessions } from "@/api/archiver";
import { fetchMyAnalyses } from "@/api/analyses";
import { fetchCuratorSessions } from "@/api/curator";
import { listIdeals } from "@/api/navigator";
import { fetchScraps } from "@/api/scraps";
import type { IdealResponse } from "@/api/types/navigator";
import type { AnalysisResultItem } from "@/lib/analyses/types";
import { IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { buildSidebarScraps } from "@/lib/sidebar/build-sidebar-scraps";
import type { SidebarChat, SidebarScrap } from "@/lib/sidebar/types";

/** 적용 중 이상향 → 없으면 최신 분석 페르소나로 사이드바 라벨 파생. */
function deriveActiveLabel(
  ideals: IdealResponse[],
  analyses: AnalysisResultItem[],
): string | null {
  const active = ideals.find((i) => i.is_active);
  if (active) return active.persona_label || IDEAL_TYPE_LABEL[active.ideal_type];
  const latest = analyses.find((a) => a.status === "completed");
  return latest?.title ?? null;
}

// 요청 합치기 — 진행 중 promise 공유(동시 호출) + 최근 로드 캐시(순차 호출).
// 순차 호출(예: ShellLayout 로드 완료 후 페이지 마운트)까지 1번으로 줄이려 짧은 TTL 사용.
// 뮤테이션(적용·삭제)은 refresh*가 강제 재조회하므로 TTL이 신선도를 해치지 않는다.
const FRESH_MS = 3000;
let idealsInflight: Promise<IdealResponse[]> | null = null;
let analysesInflight: Promise<AnalysisResultItem[]> | null = null;
let idealsLoadedAt = 0;
let analysesLoadedAt = 0;

export function formatRelativeTime(iso: string): string {
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
  /** 이상향·분석 목록 — 사이드바·허브 공용 단일 소스 (persist 안 함) */
  ideals: IdealResponse[];
  analyses: AnalysisResultItem[];
  scraps: SidebarScrap[];
  chats: SidebarChat[];
  /** 분석 상세 페이지별 큐레이터 대화 기록 (분석 id → 마지막 대화 정보).
   * customTitle이 true면 유저가 직접 이름을 바꾼 것 — 자동 기록(recordAnalysisChat)이
   * 덮어쓰지 않는다. */
  analysisChats: Record<
    string,
    { title: string; updatedAt: string; customTitle?: boolean }
  >;
  setActiveIdealLabel: (label: string | null) => void;
  /** 이상향/분석 목록 로드 (동시 호출은 dedupe). 마운트마다 호출해도 안전. */
  loadIdeals: () => Promise<void>;
  loadAnalyses: () => Promise<void>;
  /** 뮤테이션(적용·삭제·확정) 후 강제 재조회. */
  refreshIdeals: () => Promise<void>;
  refreshAnalyses: () => Promise<void>;
  removeAnalysis: (id: string) => void;
  /** 적용 중 이상향의 페르소나 → 없으면 최신 분석 페르소나로 라벨 해석 */
  loadIdealPersona: () => Promise<void>;
  loadChats: () => Promise<void>;
  loadScraps: () => Promise<void>;
  renameChat: (id: string, title: string) => void;
  deleteChat: (id: string) => void;
  clearChats: () => void;
  clearScraps: () => void;
  /** 분석 상세 페이지에서 대화가 시작/갱신될 때 기록 (사이드바 '채팅 기록'용). */
  recordAnalysisChat: (analysisId: string, title: string) => void;
  renameAnalysisChat: (analysisId: string, title: string) => void;
  removeAnalysisChat: (analysisId: string) => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set, get) => ({
      activeIdealLabel: null,
      ideals: [],
      analyses: [],
      scraps: [],
      chats: [],
      analysisChats: {},
      setActiveIdealLabel: (activeIdealLabel) => set({ activeIdealLabel }),

      recordAnalysisChat: (analysisId, title) =>
        set((s) => {
          const existing = s.analysisChats[analysisId];
          // 유저가 직접 이름을 바꾼 항목은 자동 기록으로 덮어쓰지 않는다 (시간만 갱신).
          if (existing?.customTitle) {
            return {
              analysisChats: {
                ...s.analysisChats,
                [analysisId]: { ...existing, updatedAt: new Date().toISOString() },
              },
            };
          }
          return {
            analysisChats: {
              ...s.analysisChats,
              [analysisId]: { title, updatedAt: new Date().toISOString() },
            },
          };
        }),

      renameAnalysisChat: (analysisId, title) =>
        set((s) => {
          const existing = s.analysisChats[analysisId];
          if (!existing) return s;
          return {
            analysisChats: {
              ...s.analysisChats,
              [analysisId]: { ...existing, title, customTitle: true },
            },
          };
        }),

      removeAnalysisChat: (analysisId) =>
        set((s) => {
          const next = { ...s.analysisChats };
          delete next[analysisId];
          return { analysisChats: next };
        }),

      loadAnalyses: async () => {
        if (analysesInflight) {
          await analysesInflight;
          return;
        }
        if (Date.now() - analysesLoadedAt < FRESH_MS) return; // 최근 로드 → 스킵
        analysesInflight = fetchMyAnalyses().finally(() => {
          analysesInflight = null;
        });
        try {
          set({ analyses: await analysesInflight });
          analysesLoadedAt = Date.now();
        } catch {
          /* 로그인 안 됨 등 무시 */
        }
      },

      loadIdeals: async () => {
        if (idealsInflight) {
          await idealsInflight;
          return;
        }
        if (Date.now() - idealsLoadedAt < FRESH_MS) return; // 최근 로드 → 스킵
        idealsInflight = listIdeals().finally(() => {
          idealsInflight = null;
        });
        try {
          const list = await idealsInflight;
          idealsLoadedAt = Date.now();
          set({ ideals: list });
          if (!list.some((i) => i.is_active)) {
            await get().loadAnalyses(); // 적용 이상향 없으면 분석 페르소나로 폴백
          }
          set({ activeIdealLabel: deriveActiveLabel(get().ideals, get().analyses) });
        } catch {
          /* 무시 */
        }
      },

      refreshIdeals: async () => {
        try {
          const list = await listIdeals();
          idealsLoadedAt = Date.now();
          set({ ideals: list });
          if (!list.some((i) => i.is_active)) await get().loadAnalyses();
          set({ activeIdealLabel: deriveActiveLabel(get().ideals, get().analyses) });
        } catch {
          /* 무시 */
        }
      },

      refreshAnalyses: async () => {
        try {
          set({ analyses: await fetchMyAnalyses() });
          analysesLoadedAt = Date.now();
        } catch {
          /* 무시 */
        }
      },

      removeAnalysis: (id) =>
        set((s) => ({ analyses: s.analyses.filter((a) => a.id !== id) })),

      loadIdealPersona: async () => {
        await get().loadIdeals();
      },
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
        analysisChats: s.analysisChats,
        // 목록도 캐시 → /me 재진입 시 즉시 표시 후 백그라운드 갱신(stale-while-revalidate)
        analyses: s.analyses,
        ideals: s.ideals,
      }),
    },
  ),
);
