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
  // 진짜 로그인 상태에선 항상 null이다 — 실제 액세스 토큰은 HttpOnly 쿠키에만 있고
  // JS(이 스토어 포함)는 값을 읽지 않는다. MOCK_AUTH_TOKEN일 때만 값이 있으며,
  // "목업 개발 로그인 모드인지" 표시하는 용도로만 남아 있다. 로그인 여부 판단은
  // 이제 이 필드가 아니라 user(+authReady)로 한다.
  token: string | null;
  user: AuthUser | null;
  authReady: boolean;
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
      setUser: (user) => set({ user }),
      setAuthReady: (authReady) => set({ authReady }),
      loginMock: () => {
        clearAuthFromExtension();
        set({ token: MOCK_AUTH_TOKEN, user: MOCK_USER, authReady: true });
      },
      loginDev: async () => {
        // devLogin()이 credentials:'include'로 호출되므로, 응답의 Set-Cookie로
        // access/refresh 쿠키가 이미 브라우저에 저장된 상태다 — token은 안 건드림.
        const session = await devLogin();
        set({ user: session.user, authReady: true });
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
      // token(액세스 토큰)은 localStorage에 영속화하지 않는다 — XSS에 노출되는 표면을
      // 줄이기 위해 메모리에만 유지하고, 새로고침/재방문 시엔 HttpOnly 리프레시 쿠키로
      // ShellLayout의 bootstrap이 새로 발급받는다. user는 그대로 저장해 로딩 화면
      // 없이 낙관적으로 렌더할 수 있게 유지한다.
      partialize: (s) => ({ user: s.user }),
      onRehydrateStorage: () => (state) => {
        // 저장된 user가 있으면 authReady를 즉시 true로 — 로딩 화면 없이 바로 렌더
        // (실제 token은 bootstrap의 /refresh가 채워줄 때까지 없음 — 그 사이 API 호출은
        // apiFetchAuth의 401 자동 재발급이 커버한다)
        if (state?.user) {
          state.authReady = true;
        }
      },
    },
  ),
);
