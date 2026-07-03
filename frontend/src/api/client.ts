import { refreshSession } from "@/api/auth";
import { API_BASE_URL } from "@/lib/env";
import { useAuthStore } from "@/stores/auth";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = await response.text();
    }
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
        ? (body as { detail: string }).detail
        : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/**
 * 인증이 필요한 API 호출. 액세스 토큰은 HttpOnly 쿠키로 브라우저가 자동 첨부하므로
 * 여기서 직접 헤더를 붙이지 않는다 (credentials:'include'만 있으면 됨).
 * 401(액세스 토큰 만료)이 나면 refresh 쿠키로 재발급 시도 후 원요청을 1회만 재시도한다
 * (재발급도 실패하면 완전히 로그아웃 처리 — 무한 재시도 방지).
 */
export async function apiFetchAuth<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  try {
    return await apiFetch<T>(path, { ...init, credentials: "include" });
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 401) {
      throw err;
    }

    const session = await refreshSession();
    if (!session) {
      useAuthStore.getState().logout();
      throw err;
    }

    useAuthStore.getState().setUser(session.user);
    return apiFetch<T>(path, { ...init, credentials: "include" });
  }
}
