import { useEffect } from "react";
import { Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { fetchMe } from "@/api/auth";
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

export function ShellLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { token, user, setToken, setUser } = useAuthStore();
  const openLoginModal = useShellStore((s) => s.openLoginModal);
  const isHomePage = location.pathname === ROUTES.home;
  const urlToken = searchParams.get("token");

  useEffect(() => {
    if (urlToken) setToken(urlToken);
  }, [urlToken, setToken]);

  useEffect(() => {
    const activeToken = token ?? urlToken;
    if (!activeToken || user || isMockAuthToken(activeToken)) return;
    fetchMe(activeToken).then((u) => {
      if (u) setUser(u);
    });
  }, [token, urlToken, user, setUser]);

  useEffect(() => {
    if (!token && !urlToken && !isPublicPath(location.pathname)) {
      navigate(ROUTES.login, { replace: true });
    }
  }, [token, urlToken, location.pathname, navigate]);

  useEffect(() => {
    if (location.pathname === ROUTES.login && !token && !urlToken) {
      openLoginModal();
      navigate(ROUTES.home, { replace: true });
    }
  }, [location.pathname, token, urlToken, openLoginModal, navigate]);

  const showShell =
    token || urlToken || isPublicPath(location.pathname);
  if (!showShell) {
    return null;
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
