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
import { isMockAuthToken, useAuthStore } from "@/stores/auth";
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
  const { token, user, authReady, setToken, setUser, setAuthReady } = useAuthStore();
  const prevToken = useRef<string | null>(null);
  const openLoginModal = useShellStore((s) => s.openLoginModal);
  const closeLoginModal = useShellStore((s) => s.closeLoginModal);
  const loadChats = useSidebarStore((s) => s.loadChats);
  const loadScraps = useSidebarStore((s) => s.loadScraps);
  const loadIdealPersona = useSidebarStore((s) => s.loadIdealPersona);
  const setActiveIdealLabel = useSidebarStore((s) => s.setActiveIdealLabel);
  const clearScraps = useSidebarStore((s) => s.clearScraps);
  const scrapPanelOpen = useScrapDetailPanelStore((s) => s.open);
  const selectedScrapId = useScrapDetailPanelStore((s) => s.selectedScrapId);
  const setScrapPanelOpen = useScrapDetailPanelStore((s) => s.setOpen);

  useEffect(() => {
    if (user) {
      void loadChats();
      void loadScraps();
      void loadIdealPersona();
    } else {
      clearScraps();
      setActiveIdealLabel(null);
    }
  }, [
    user,
    loadChats,
    loadScraps,
    loadIdealPersona,
    clearScraps,
    setActiveIdealLabel,
  ]);
  const isHomePage = location.pathname === ROUTES.home;

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const currentToken = useAuthStore.getState().token;
        if (currentToken && isMockAuthToken(currentToken)) {
          return;
        }

        const session = await refreshSession();
        if (cancelled) return;
        if (session) {
          // currentToken이 없을 때만 웰컴 토스트 (신규 로그인)
          const isFirstLogin = !currentToken && prevToken.current === null;
          prevToken.current = session.access_token;
          setToken(session.access_token);
          setUser(session.user);
          void syncAuthToExtension(session.access_token);
          closeLoginModal();
          if (isFirstLogin) {
            toast.success(`${session.user.name}님, 환영합니다!`);
          }
        } else if (!currentToken) {
          // 쿠키도 없고 저장된 token도 없으면 완전히 비로그인
        } else {
          // 쿠키 갱신 실패지만 저장된 token이 있으면 일단 유지
        }
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [setToken, setUser, setAuthReady, closeLoginModal]);

  /** 로그인·세션 갱신·로그아웃 시 익스텐션 chrome.storage와 동기화 */
  useEffect(() => {
    if (!authReady) return;

    if (token && user && !isMockAuthToken(token)) {
      void syncAuthToExtension(token);
      return;
    }

    if (!token) {
      clearAuthFromExtension();
    }
  }, [authReady, token, user]);

  useEffect(() => {
    if (token) closeLoginModal();
  }, [token, closeLoginModal]);

  useEffect(() => {
    if (!authReady) return;
    if (!token && !isMockAuthToken(token) && !isPublicPath(location.pathname)) {
      navigate(ROUTES.home, { replace: true });
      openLoginModal();
    }
  }, [authReady, token, location.pathname, navigate, openLoginModal]);

  useEffect(() => {
    if (!authReady) return;
    if (location.pathname === ROUTES.login && !token) {
      openLoginModal();
      navigate(ROUTES.home, { replace: true });
    }
  }, [authReady, location.pathname, token, openLoginModal, navigate]);

  if (!authReady && !isPublicPath(location.pathname)) {
    return <AuthLoading />;
  }

  const canShowShell =
    Boolean(token) || isMockAuthToken(token) || isPublicPath(location.pathname);

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
