import { ensureFreshAuthSession } from '@/shared/api/extensionAuth'
import { API_BASE } from '@/shared/api/config'
import {
  clearAuthSession,
  readAuthSession,
  storeAuthSession,
} from '@/shared/auth/sessionStorage'

export { API_BASE }

/**
 * 익스텐션 ↔ backend API 통신 계층.
 */
export interface TrackingPayload {
  url: string
  pageTitle: string
  durationSeconds: number
  timestamp: string
}

/**
 * Archiver 등 인증 API용 Bearer 헤더.
 * extension refresh로 access 자동 갱신.
 */
export async function getAuthHeaders(
  extra: Record<string, string> = {},
): Promise<Record<string, string>> {
  let session = await readAuthSession()

  if (session) {
    const fresh = await ensureFreshAuthSession(session)
    if (fresh) {
      if (
        fresh.access_token !== session.access_token ||
        fresh.refresh_token !== session.refresh_token
      ) {
        await storeAuthSession(fresh)
      }
      session = fresh
    } else {
      await clearAuthSession()
      session = null
    }
  }

  const token = session?.access_token ?? null

  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/**
 * 정산된 페이지 체류 세션을 backend DB로 전송한다.
 */
export async function sendTrackingData(payload: TrackingPayload): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/tracking/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Tracking API error: ${response.status}`)
  }
}
