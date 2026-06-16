import { API_BASE_URL } from "@/lib/env";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture: string | null;
}

export interface DevLoginResponse {
  access_token: string;
  user: AuthUser;
}

export async function fetchMe(token: string): Promise<AuthUser | null> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}

/** 로컬 개발용 — Google OAuth 없이 즉시 로그인 */
export async function devLogin(): Promise<DevLoginResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/dev-login`, {
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "로그인에 실패했습니다. 백엔드가 실행 중인지 확인하세요.",
    );
  }
  return res.json();
}
