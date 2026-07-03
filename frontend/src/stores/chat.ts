import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface VideoItem {
  title: string;
  channel: string;
}

export interface RankItem {
  label: string;
  count: number;
}

export interface RadarItem {
  axis: string;
  current: number;
  ideal: number | null;
}

export type ChartEntry =
  | { type: "video_list"; title: string; items: VideoItem[] }
  | { type: "shorts_list"; title: string; items: VideoItem[] }
  | { type: "channel_rank"; title: string; items: RankItem[] }
  | { type: "category_bar"; title: string; items: RankItem[] }
  | { type: "persona_radar"; title: string; items: RadarItem[] };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  imageUrl?: string;
  status?: string;
  streaming?: boolean;
  createdAt?: number;
  chartData?: ChartEntry[];
}

interface ChatState {
  sessions: Record<string, ChatMessage[]>;
  sessionId: string;
  isStreaming: boolean;

  // 현재 세션 메시지 (sessions[sessionId])
  messages: ChatMessage[];

  addUserMessage: (content: string, imageUrl?: string) => string;
  startAssistantMessage: () => string;
  appendToken: (id: string, token: string) => void;
  setStatus: (id: string, status: string) => void;
  addChartEntry: (id: string, entry: ChartEntry) => void;
  finishAssistantMessage: (id: string) => void;
  clearMessages: () => void;
  setSession: (sessionId: string, messages: ChatMessage[]) => void;
}

function randomId() {
  return Math.random().toString(36).slice(2, 10);
}

function withSessions(
  s: ChatState,
  updatedMessages: ChatMessage[],
): Partial<ChatState> {
  return {
    messages: updatedMessages,
    sessions: { ...s.sessions, [s.sessionId]: updatedMessages },
  };
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessions: {},
      sessionId: randomId(),
      isStreaming: false,
      messages: [],

      addUserMessage: (content, imageUrl) => {
        const id = randomId();
        set((s) => {
          const updated = [...s.messages, { id, role: "user" as const, content, imageUrl, createdAt: Date.now() }];
          return withSessions(s, updated);
        });
        return id;
      },

      startAssistantMessage: () => {
        const id = randomId();
        set((s) => {
          const updated = [
            ...s.messages,
            { id, role: "assistant" as const, content: "", status: "...", streaming: true, createdAt: Date.now() },
          ];
          return { ...withSessions(s, updated), isStreaming: true };
        });
        return id;
      },

      appendToken: (id, token) => {
        set((s) => {
          const updated = s.messages.map((m) =>
            m.id === id ? { ...m, content: m.content + token, status: undefined } : m,
          );
          return withSessions(s, updated);
        });
      },

      setStatus: (id, status) => {
        set((s) => {
          const updated = s.messages.map((m) =>
            m.id === id ? { ...m, status } : m,
          );
          return withSessions(s, updated);
        });
      },

      addChartEntry: (id, entry) => {
        set((s) => {
          const updated = s.messages.map((m) =>
            m.id === id ? { ...m, chartData: [...(m.chartData ?? []), entry] } : m,
          );
          return withSessions(s, updated);
        });
      },

      finishAssistantMessage: (id) => {
        set((s) => {
          const updated = s.messages.map((m) =>
            m.id === id ? { ...m, streaming: false, status: undefined } : m,
          );
          return { ...withSessions(s, updated), isStreaming: false };
        });
      },

      clearMessages: () => {
        const newId = randomId();
        set((s) => ({
          sessions: { ...s.sessions, [s.sessionId]: [] },
          sessionId: newId,
          messages: [],
          isStreaming: false,
        }));
      },

      // 현재 세션을 sessions에 저장한 뒤 새 세션으로 전환
      setSession: (newSessionId, newMessages) =>
        set((s) => ({
          sessions: {
            ...s.sessions,
            [s.sessionId]: s.messages,   // 현재 세션 보존
            [newSessionId]: newMessages,  // 새 세션 캐시
          },
          sessionId: newSessionId,
          messages: newMessages,
          isStreaming: false,
        })),
    }),
    {
      name: "synapse-chat",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({
        sessions: Object.fromEntries(
          Object.entries(s.sessions)
            .slice(-10) // 최대 10개 세션만 저장
            .map(([k, msgs]) => [
              k,
              msgs.filter((m) => !m.streaming).map((m) => ({ ...m, status: undefined })),
            ]),
        ),
        sessionId: s.sessionId,
        messages: s.messages
          .filter((m) => !m.streaming)
          .map((m) => ({ ...m, status: undefined })),
      }),
    },
  ),
);
