import { useEffect, useRef } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { refreshSession } from "@/api/auth";
import { LoginModal } from "@/components/auth/login-modal";
import { ScrapDetailPanel } from "@/components/scraps/scrap-detail-panel";
import { Sidebar } from "@/components/shell/Sidebar";
import {
  clearAuthFromExtension,
  syncAuthToExtension,
} from "@/lib/extension-auth-sync";
import { ROUTES } from "@/routes";
import { type AuthUser, isMockAuthToken, useAuthStore } from "@/stores/auth";
import { useShellStore } from "@/stores/shell";
import { useScrapDetailPanelStore } from "@/stores/scrap-detail-panel";
import { useSidebarStore } from "@/stores/sidebar";

function isPublicPath(pathname: string) {
  if (pathname === ROUTES.home || pathname === ROUTES.login) return true;
  if (pathname === ROUTES.trends || pathname === ROUTES.download) return true;
  return pathname.startsWith("/agents");
}

function AuthLoading() {
  return (
    <div className="flex h-screen items-center justify-center bg-background text-sm text-muted-foreground">
      세션 확인 중…
    </div>
  );
}

export function ShellLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  // token은 이제 진짜 로그인 상태에선 항상 null — 목업 개발 로그인 모드 판별용으로만 남아있다.
  // 실제 로그인 여부는 user(+authReady)로 판단한다.
  const { token, user, authReady, setUser, setAuthReady } = useAuthStore();
  const prevUser = useRef<AuthUser | null>(null);
  const openLoginModal = useShellStore((s) => s.openLoginModal);
  const closeLoginModal = useShellStore((s) => s.closeLoginModal);
  const loadChats = useSidebarStore((s) => s.loadChats);
  const loadScraps = useSidebarStore((s) => s.loadScraps);
  const clearScraps = useSidebarStore((s) => s.clearScraps);
  const scrapPanelOpen = useScrapDetailPanelStore((s) => s.open);
  const selectedScrapId = useScrapDetailPanelStore((s) => s.selectedScrapId);
  const setScrapPanelOpen = useScrapDetailPanelStore((s) => s.setOpen);

  useEffect(() => {
    if (user) {
      void loadChats();
      void loadScraps();
    } else {
      clearScraps();
    }
  }, [user, loadChats, loadScraps, clearScraps]);
  const isHomePage = location.pathname === ROUTES.home;

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const currentToken = useAuthStore.getState().token;
        if (currentToken && isMockAuthToken(currentToken)) {
          return;
        }

        const currentUser = useAuthStore.getState().user;
        // /refresh는 이제 access token을 쿠키로 세팅한다 — 여기선 user만 저장하면 된다.
        const session = await refreshSession();
        if (cancelled) return;
        if (session) {
          // 이전에 로그인된 유저가 없었을 때만 웰컴 토스트 (신규 로그인)
          const isFirstLogin = !currentUser && prevUser.current === null;
          prevUser.current = session.user;
          setUser(session.user);
          void syncAuthToExtension();
          closeLoginModal();
          if (isFirstLogin) {
            toast.success(`${session.user.name}님, 환영합니다!`);
          }
        } else if (!currentUser) {
          // 쿠키도 없고 저장된 user도 없으면 완전히 비로그인
        } else {
          // 쿠키 갱신 실패지만 저장된 user가 있으면 일단 유지
        }
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [setUser, setAuthReady, closeLoginModal]);

  /** 로그인·세션 갱신·로그아웃 시 익스텐션 chrome.storage와 동기화 */
  useEffect(() => {
    if (!authReady) return;

    if (user && !isMockAuthToken(token)) {
      void syncAuthToExtension();
      return;
    }

    if (!user) {
      clearAuthFromExtension();
    }
  }, [authReady, token, user]);

  useEffect(() => {
    if (user) closeLoginModal();
  }, [user, closeLoginModal]);

  useEffect(() => {
    if (!authReady) return;
    if (!user && !isPublicPath(location.pathname)) {
      navigate(ROUTES.home, { replace: true });
      openLoginModal();
    }
  }, [authReady, user, location.pathname, navigate, openLoginModal]);

  useEffect(() => {
    if (!authReady) return;
    if (location.pathname === ROUTES.login && !user) {
      openLoginModal();
      navigate(ROUTES.home, { replace: true });
    }
  }, [authReady, location.pathname, user, openLoginModal, navigate]);

  if (!authReady && !isPublicPath(location.pathname)) {
    return <AuthLoading />;
  }

  const canShowShell = Boolean(user) || isPublicPath(location.pathname);

  if (!canShowShell) {
    return <AuthLoading />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main
        className={`flex min-h-0 flex-1 flex-col ${
          isHomePage ? "overflow-hidden" : "overflow-y-auto"
        }`}
      >
        <Outlet />
      </main>
      <LoginModal />
      <ScrapDetailPanel
        scrapId={selectedScrapId}
        open={scrapPanelOpen}
        onOpenChange={setScrapPanelOpen}
      />
    </div>
  );
}
