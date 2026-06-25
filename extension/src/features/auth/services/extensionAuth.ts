import { API_BASE } from '@/shared/api/config'
import type { AuthSessionSnapshot } from '@/shared/auth/types'

interface ExtensionSessionResponse {
  access_token: string
  refresh_token: string
  user: AuthSessionSnapshot['user']
}

/** JWT exp 클레임 기준 access 만료 여부 (검증 없이 exp만 확인) */
export function isAccessTokenExpired(accessToken: string, bufferSeconds = 60): boolean {
  try {
    const payloadPart = accessToken.split('.')[1]
    if (!payloadPart) return true
    const payload = JSON.parse(atob(payloadPart)) as { exp?: number }
    if (typeof payload.exp !== 'number') return true
    return payload.exp * 1000 <= Date.now() + bufferSeconds * 1000
  } catch {
    return true
  }
}

export async function exchangeExtensionCode(code: string): Promise<AuthSessionSnapshot> {
  const response = await fetch(`${API_BASE}/api/v1/auth/extension-exchange`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })

  if (!response.ok) {
    throw new Error(`extension-exchange failed: ${response.status}`)
  }

  const data = (await response.json()) as ExtensionSessionResponse
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: data.user,
  }
}

export async function refreshExtensionSession(
  refreshToken: string,
): Promise<AuthSessionSnapshot> {
  const response = await fetch(`${API_BASE}/api/v1/auth/extension-refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    throw new Error(`extension-refresh failed: ${response.status}`)
  }

  const data = (await response.json()) as ExtensionSessionResponse
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: data.user,
  }
}

export async function revokeExtensionSession(refreshToken: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/auth/extension-revoke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

/** access 만료 시 refresh, 실패 시 null */
export async function ensureFreshAuthSession(
  session: AuthSessionSnapshot,
): Promise<AuthSessionSnapshot | null> {
  if (!isAccessTokenExpired(session.access_token)) {
    return session
  }

  try {
    return await refreshExtensionSession(session.refresh_token)
  } catch {
    return null
  }
}
