import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthUser {
  id: number;
  email: string;
  name: string;
  picture: string | null;
}

interface AuthStore {
  token: string | null;
  user: AuthUser | null;
  setToken: (token: string) => void;
  setUser: (user: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "synapse-auth" },
  ),
);
