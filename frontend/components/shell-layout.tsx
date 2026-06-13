"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/stores/auth";
import { Sidebar } from "@/components/sidebar";

export function ShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, setToken } = useAuthStore();
  const isLoginPage = pathname === "/login";
  const urlToken = searchParams.get("token");

  // OAuth 콜백 토큰을 ShellLayout에서 즉시 저장 (auth guard보다 먼저)
  useEffect(() => {
    if (urlToken) setToken(urlToken);
  }, [urlToken, setToken]);

  useEffect(() => {
    if (!token && !urlToken && !isLoginPage) {
      router.replace("/login");
    }
  }, [token, urlToken, isLoginPage, router]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (!token && !urlToken) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
