import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface ChatTheme {
  id: string;
  name: string;
  bubble: string;
}

export const CHAT_THEMES: ChatTheme[] = [
  { id: "default", name: "기본",   bubble: "hsl(221,83%,53%)" },
  { id: "purple",  name: "보라",   bubble: "linear-gradient(135deg,#7c3aed,#a855f7)" },
  { id: "pink",    name: "핑크",   bubble: "linear-gradient(135deg,#ec4899,#f43f5e)" },
  { id: "rose",    name: "로즈",   bubble: "linear-gradient(135deg,#f43f5e,#fb923c)" },
  { id: "green",   name: "초록",   bubble: "linear-gradient(135deg,#10b981,#059669)" },
  { id: "teal",    name: "청록",   bubble: "linear-gradient(135deg,#06b6d4,#3b82f6)" },
  { id: "indigo",  name: "인디고", bubble: "linear-gradient(135deg,#4f46e5,#7c3aed)" },
  { id: "orange",  name: "오렌지", bubble: "linear-gradient(135deg,#f59e0b,#ef4444)" },
  { id: "amber",   name: "골드",   bubble: "linear-gradient(135deg,#f59e0b,#84cc16)" },
  { id: "dark",    name: "다크",   bubble: "linear-gradient(135deg,#1f2937,#374151)" },
  { id: "mint",    name: "민트",   bubble: "linear-gradient(135deg,#34d399,#06b6d4)" },
  { id: "lavender",name: "라벤더", bubble: "linear-gradient(135deg,#a78bfa,#ec4899)" },
  { id: "sunset",  name: "선셋",   bubble: "linear-gradient(135deg,#f97316,#ec4899)" },
  { id: "ocean",   name: "오션",   bubble: "linear-gradient(135deg,#0ea5e9,#10b981)" },
  { id: "cherry",  name: "체리",   bubble: "linear-gradient(135deg,#be123c,#9f1239)" },
];

interface ChatThemeState {
  themeId: string;
  hasSeenTip: boolean;
  setTheme: (id: string) => void;
  markTipSeen: () => void;
  currentTheme: () => ChatTheme;
}

export const useChatThemeStore = create<ChatThemeState>()(
  persist(
    (set, get) => ({
      themeId: "default",
      hasSeenTip: false,
      setTheme: (id) => set({ themeId: id }),
      markTipSeen: () => set({ hasSeenTip: true }),
      currentTheme: () =>
        CHAT_THEMES.find((t) => t.id === get().themeId) ?? CHAT_THEMES[0],
    }),
    {
      name: "synapse-chat-theme",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
