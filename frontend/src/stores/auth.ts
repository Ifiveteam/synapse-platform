import { create } from "zustand";
import { toast } from "sonner";

import { logoutSession } from "@/api/auth";
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
  logout: () => void;
}

export function isMockAuthToken(token: string | null) {
  return token === MOCK_AUTH_TOKEN;
}

export const useAuthStore = create<AuthStore>()((set) => ({
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
  logout: () => {
    void logoutSession();
    clearAuthFromExtension();
    set({ token: null, user: null, authReady: true });
    toast.success("로그아웃 되었습니다");
  },
}));
