import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { LoginPanel } from "@/components/auth/login-panel";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (user) navigate(ROUTES.home, { replace: true });
  }, [user, navigate]);

  return (
    <main className="bg-background flex min-h-screen items-center justify-center p-4">
      <LoginPanel />
    </main>
  );
}
