/**
 * Scrap 생성 요청 — content script → background 프록시 프로토콜.
 *
 * content script(FAB)는 웹 페이지 origin으로 fetch 시 CORS preflight가 차단되므로
 * Service Worker가 host_permissions 하에서 API를 대신 호출한다.
 */
import type { ScrapCreateRequest, ScrapResponse } from '@/features/scrap/models/types'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export const CREATE_SCRAP_ACTION = 'CREATE_SCRAP' as const

export interface CreateScrapMessage {
  action: typeof CREATE_SCRAP_ACTION
  payload: ScrapCreateRequest
}

export interface CreateScrapResult {
  ok: boolean
  data?: ScrapResponse
  error?: string
}

/** Background Service Worker에 스크랩 생성을 위임한다. */
export function submitScrapCreateViaBackground(
  payload: ScrapCreateRequest,
): Promise<ScrapResponse> {
  return new Promise((resolve, reject) => {
    if (!isExtensionContextValid()) {
      reject(new Error('익스텐션 컨텍스트가 유효하지 않습니다.'))
      return
    }

    const message: CreateScrapMessage = {
      action: CREATE_SCRAP_ACTION,
      payload,
    }

    chrome.runtime.sendMessage(message, (response: CreateScrapResult | undefined) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message))
        return
      }
      if (!response?.ok || !response.data) {
        reject(new Error(response?.error ?? '스크랩 저장에 실패했습니다.'))
        return
      }
      resolve(response.data)
    })
  })
}
