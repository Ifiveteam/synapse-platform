import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  picture: string | null;
}

export const MOCK_AUTH_TOKEN = "mock-dev-token";

const MOCK_USER: AuthUser = {
  id: 1,
  email: "dev@synapse.local",
  name: "Synapse Dev",
  picture: null,
};

interface AuthStore {
  token: string | null;
  user: AuthUser | null;
  setToken: (token: string) => void;
  setUser: (user: AuthUser) => void;
  loginMock: () => void;
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
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      loginMock: () => set({ token: MOCK_AUTH_TOKEN, user: MOCK_USER }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "synapse-auth" },
  ),
);
