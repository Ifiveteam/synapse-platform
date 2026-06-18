import { create } from "zustand";

import { logoutSession } from "@/api/auth";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture: string | null;
}

export const MOCK_AUTH_TOKEN = "mock-dev-token";

const MOCK_USER: AuthUser = {
  id: "mock-guest",
  email: "dev@synapse.local",
  name: "Synapse Dev",
  picture: null,
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
  loginMock: () => set({ token: MOCK_AUTH_TOKEN, user: MOCK_USER, authReady: true }),
  logout: () => {
    void logoutSession();
    set({ token: null, user: null, authReady: true });
  },
}));
