/**
 * 익스텐션 ↔ backend API 통신 계층.
 * API Key 등 민감 정보는 서버에만 두고, 클라이언트는 REST 엔드포인트로만 소통한다.
 */
export interface TrackingPayload {
  url: string
  pageTitle: string
  durationSeconds: number
  timestamp: string
}

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export { API_BASE }

/**
 * 정산된 페이지 체류 세션을 backend DB로 전송한다.
 * sessionManager.endCurrentSession()에서 fire-and-forget으로 호출된다.
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
