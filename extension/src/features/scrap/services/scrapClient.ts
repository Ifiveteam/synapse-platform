/**
 * Scrap 백엔드 클라이언트 — REST 호출 SSOT.
 *
 * 프로토콜: backend `app/api/v1/scrap.py`
 * envelope: { status: "success", data: T | T[] }
 */
import type { ScrapCreateRequest, ScrapResponse } from '@/features/scrap/models/types'
import { API_BASE } from '@/shared/api/config'
import { getAuthHeaders } from '@/shared/api/client'

interface ApiItemResponse<T> {
  status: string
  data: T
}

interface ApiListResponse<T> {
  status: string
  data: T[]
}

async function parseApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | { msg?: string }[] }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg
    }
  } catch {
    // ignore JSON parse failure
  }
  return `scraps API failed: ${response.status}`
}

/** POST /api/v1/scraps — Gemini 파이프라인으로 스크랩 생성 */
export async function createScrap(payload: ScrapCreateRequest): Promise<ScrapResponse> {
  const response = await fetch(`${API_BASE}/api/v1/scraps`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }

  const body = (await response.json()) as ApiItemResponse<ScrapResponse>
  return body.data
}

/** GET /api/v1/scraps — 본인 스크랩 목록 (최신순) */
export async function getScraps(): Promise<ScrapResponse[]> {
  const response = await fetch(`${API_BASE}/api/v1/scraps`, {
    headers: await getAuthHeaders(),
  })

  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }

  const body = (await response.json()) as ApiListResponse<ScrapResponse>
  return body.data ?? []
}

/** DELETE /api/v1/scraps/{id} */
export async function deleteScrap(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/scraps/${id}`, {
    method: 'DELETE',
    headers: await getAuthHeaders(),
  })

  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }
}
