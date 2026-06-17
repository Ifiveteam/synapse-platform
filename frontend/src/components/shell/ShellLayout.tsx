import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { refreshSession } from "@/api/auth";
import { LoginModal } from "@/components/auth/login-modal";
import { Sidebar } from "@/components/shell/Sidebar";
import { ROUTES } from "@/routes";
import { isMockAuthToken, useAuthStore } from "@/stores/auth";
import { useShellStore } from "@/stores/shell";

function isPublicPath(pathname: string) {
  if (pathname === ROUTES.home || pathname === ROUTES.login) return true;
  if (pathname === ROUTES.trends) return true;
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
  const { token, authReady, setToken, setUser, setAuthReady } = useAuthStore();
  const openLoginModal = useShellStore((s) => s.openLoginModal);
  const isHomePage = location.pathname === ROUTES.home;

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const currentToken = useAuthStore.getState().token;
        if (currentToken && isMockAuthToken(currentToken)) {
          return;
        }
        if (currentToken) {
          return;
        }

        const session = await refreshSession();
        if (cancelled) return;
        if (session) {
          setToken(session.access_token);
          setUser(session.user);
        }
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [setToken, setUser, setAuthReady]);

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

  if (!authReady) {
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
    </div>
  );
}
