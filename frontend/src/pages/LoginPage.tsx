import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { LoginPanel } from "@/components/auth/login-panel";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (token) navigate(ROUTES.home, { replace: true });
  }, [token, navigate]);

  return (
    <main className="bg-background flex min-h-screen items-center justify-center p-4">
      <LoginPanel />
    </main>
  );
}
