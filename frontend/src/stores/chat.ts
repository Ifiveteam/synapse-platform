import { create } from "zustand";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: string;
  streaming?: boolean;
}

interface ChatState {
  messages: ChatMessage[];
  sessionId: string;
  isStreaming: boolean;

  addUserMessage: (content: string) => string;
  startAssistantMessage: () => string;
  appendToken: (id: string, token: string) => void;
  setStatus: (id: string, status: string) => void;
  finishAssistantMessage: (id: string) => void;
  clearMessages: () => void;
}

function randomId() {
  return Math.random().toString(36).slice(2, 10);
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: randomId(),
  isStreaming: false,

  addUserMessage: (content) => {
    const id = randomId();
    set((s) => ({
      messages: [...s.messages, { id, role: "user", content }],
    }));
    return id;
  },

  startAssistantMessage: () => {
    const id = randomId();
    set((s) => ({
      isStreaming: true,
      messages: [
        ...s.messages,
        { id, role: "assistant", content: "", status: "...", streaming: true },
      ],
    }));
    return id;
  },

  appendToken: (id, token) => {
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token, status: undefined } : m,
      ),
    }));
  },

  setStatus: (id, status) => {
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, status } : m,
      ),
    }));
  },

  finishAssistantMessage: (id) => {
    set((s) => ({
      isStreaming: false,
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, streaming: false, status: undefined } : m,
      ),
    }));
  },

  clearMessages: () => set({ messages: [], sessionId: randomId() }),
}));
