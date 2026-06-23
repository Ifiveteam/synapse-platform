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

export async function updateMe(
  token: string,
  data: { nickname?: string; picture?: string },
): Promise<AuthUser | null> {
  const res = await fetch(`${AUTH_API}/me`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function deleteMe(token: string): Promise<boolean> {
  const res = await fetch(`${AUTH_API}/me`, {
    method: "DELETE",
    credentials: "include",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.ok;
}

export async function logoutSession(): Promise<void> {
  await fetch(`${AUTH_API}/logout`, {
    method: "POST",
    credentials: "include",
  });
}
