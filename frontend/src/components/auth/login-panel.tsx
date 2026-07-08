import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { PentagonGraph } from "@/components/home/pentagon-graph";
import { API_BASE_URL } from "@/lib/env";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";
import { useShellStore } from "@/stores/shell";

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
        fill="#EA4335"
      />
    </svg>
  );
}

export function LoginPanel() {
  const navigate = useNavigate();
  const loginMock = useAuthStore((s) => s.loginMock);
  const loginDev = useAuthStore((s) => s.loginDev);
  const closeLoginModal = useShellStore((s) => s.closeLoginModal);

  // 실제 Google OAuth: 백엔드 /auth/login → 구글 동의 → 콜백(쿠키) → 메인(/)
  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE_URL}/api/v1/auth/login`;
  };

  // 개발 편의: 백엔드 dev-login으로 즉시 진입 (실 JWT). 실패 시 목 토큰 폴백.
  const handleGuestLogin = async () => {
    try {
      await loginDev();
    } catch {
      loginMock();
    }
    closeLoginModal();
    navigate(ROUTES.home);
  };

  return (
    <div className="w-full max-w-md">
      <div className="border-border overflow-hidden rounded-2xl border bg-card">
        <div className="border-border relative border-b bg-secondary/40 px-4 pt-4 pb-4">
          <PentagonGraph />
        </div>

        <div className="px-6 py-6 text-center">
          <h2 className="text-xl font-semibold tracking-tight">
            Synapse 시작하기
          </h2>
          <p className="text-muted-foreground mt-1.5 text-sm">
            Google 계정으로 연결하세요
          </p>

          <button
            type="button"
            onClick={handleGoogleLogin}
            className="border-border hover:bg-secondary mt-6 flex w-full items-center gap-3 rounded-full border bg-card px-5 py-3.5 text-sm font-medium transition-colors"
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-white shadow-sm">
              <GoogleIcon />
            </span>
            <span className="flex-1 text-left">Google로 계속하기</span>
            <ArrowRight size={16} className="text-muted-foreground" />
          </button>

          <button
            type="button"
            onClick={handleGuestLogin}
            className="text-muted-foreground hover:text-foreground mt-3 w-full text-xs underline-offset-4 transition-colors hover:underline"
          >
            게스트로 둘러보기 (개발용)
          </button>

          <p className="text-muted-foreground mt-5 text-xs">
            가입 시 이용약관에 동의하는 것으로 간주됩니다
          </p>
        </div>
      </div>
    </div>
  );
}
