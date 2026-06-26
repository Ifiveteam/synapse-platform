import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toast } from "sonner";

import { devLogin, logoutSession } from "@/api/auth";
import { clearAuthFromExtension } from "@/lib/extension-auth-sync";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture: string | null;
  plan: string;
}

export const MOCK_AUTH_TOKEN = "mock-dev-token";

const MOCK_USER: AuthUser = {
  id: "mock-guest",
  email: "dev@synapse.local",
  name: "Synapse Dev",
  picture: null,
  plan: "free",
};

interface AuthStore {
  token: string | null;
  user: AuthUser | null;
  authReady: boolean;
  setToken: (token: string) => void;
  setUser: (user: AuthUser) => void;
  setAuthReady: (ready: boolean) => void;
  loginMock: () => void;
  loginDev: () => Promise<void>;
  logout: () => void;
}

export function isMockAuthToken(token: string | null) {
  return token === MOCK_AUTH_TOKEN;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      authReady: false,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setAuthReady: (authReady) => set({ authReady }),
      loginMock: () => {
        clearAuthFromExtension();
        set({ token: MOCK_AUTH_TOKEN, user: MOCK_USER, authReady: true });
      },
      loginDev: async () => {
        const session = await devLogin();
        set({
          token: session.access_token,
          user: session.user,
          authReady: true,
        });
      },
      logout: () => {
        void logoutSession();
        clearAuthFromExtension();
        set({ token: null, user: null, authReady: true });
        toast.success("로그아웃 되었습니다");
      },
    }),
    {
      name: "synapse-auth",
      partialize: (s) => ({ token: s.token, user: s.user }),
      onRehydrateStorage: () => (state) => {
        // 저장된 token이 있으면 authReady를 즉시 true로 — 로딩 화면 없이 바로 렌더
        if (state?.token) {
          state.authReady = true;
        }
      },
    },
  ),
);
