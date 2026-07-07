import { API_BASE_URL } from "@/lib/env";

const AUTH_API = `${API_BASE_URL}/api/v1/auth`;

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture: string | null;
  plan: string;
}

export interface SessionResponse {
  access_token: string;
  user: AuthUser;
}

export interface ExtensionCodeResponse {
  code: string;
  expires_in: number;
}

export async function fetchMe(token: string): Promise<AuthUser | null> {
  const res = await fetch(`${AUTH_API}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}

/**
 * refresh 쿠키(httpOnly)로 access token 재발급.
 *
 * refresh token은 호출마다 회전(rotate)되므로 동시에 두 번 호출하면
 * 두 번째가 이미 무효가 된 쿠키로 401이 난다. (React StrictMode가 부팅
 * effect를 2번 실행하는 dev 환경에서 로그인이 풀리는 원인) → 진행 중인
 * 요청 하나를 공유해 중복 호출을 합친다.
 */
let inFlightRefresh: Promise<SessionResponse | null> | null = null;

export function refreshSession(): Promise<SessionResponse | null> {
  if (inFlightRefresh) return inFlightRefresh;

  inFlightRefresh = (async () => {
    try {
      const res = await fetch(`${AUTH_API}/refresh`, {
        method: "POST",
        credentials: "include",
        signal: AbortSignal.timeout(8_000),
      });
      if (!res.ok) return null;
      return (await res.json()) as SessionResponse;
    } catch {
      return null;
    } finally {
      inFlightRefresh = null;
    }
  })();

  return inFlightRefresh;
}

/** 웹 로그인 세션으로 익스텐션 1회용 연동 code 발급 */
export async function issueExtensionAuthCode(
  accessToken?: string | null,
): Promise<ExtensionCodeResponse | null> {
  try {
    const res = await fetch(`${AUTH_API}/extension-code`, {
      method: "POST",
      credentials: "include",
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      signal: AbortSignal.timeout(8_000),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/** 개발용 즉시 로그인 — 실제 JWT 발급 (게스트 진입) */
export async function devLogin(): Promise<SessionResponse> {
  const res = await fetch(`${AUTH_API}/dev-login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`dev-login failed (${res.status})`);
  return res.json();
}

export async function updateMe(
  data: { nickname?: string; picture?: string },
): Promise<AuthUser | null> {
  const res = await fetch(`${AUTH_API}/me`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function deleteMe(): Promise<boolean> {
  const res = await fetch(`${AUTH_API}/me`, {
    method: "DELETE",
    credentials: "include",
  });
  return res.ok;
}

export async function logoutSession(): Promise<void> {
  await fetch(`${AUTH_API}/logout`, {
    method: "POST",
    credentials: "include",
  });
}
