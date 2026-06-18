import { API_BASE_URL } from "@/lib/env";

const AUTH_API = `${API_BASE_URL}/api/v1/auth`;

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture: string | null;
}

export interface SessionResponse {
  access_token: string;
  user: AuthUser;
}

export async function fetchMe(token: string): Promise<AuthUser | null> {
  const res = await fetch(`${AUTH_API}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}

/** refresh 쿠키(httpOnly)로 access token 재발급 */
export async function refreshSession(): Promise<SessionResponse | null> {
  try {
    const res = await fetch(`${AUTH_API}/refresh`, {
      method: "POST",
      credentials: "include",
      signal: AbortSignal.timeout(8_000),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/** 로컬 개발용 — Google OAuth 없이 즉시 로그인 */
export async function devLogin(): Promise<SessionResponse> {
  const res = await fetch(`${AUTH_API}/dev-login`, {
    method: "POST",
    credentials: "include",
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

export async function logoutSession(): Promise<void> {
  await fetch(`${AUTH_API}/logout`, {
    method: "POST",
    credentials: "include",
  });
}
