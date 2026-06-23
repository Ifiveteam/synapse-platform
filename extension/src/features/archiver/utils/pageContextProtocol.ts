/** content script ↔ sidepanel 페이지 본문 추출 메시지 프로토콜 */

export const SYNAPSE_EXTRACT_PAGE_TEXT = 'SYNAPSE_EXTRACT_PAGE_TEXT' as const

/** 탑프레임 ↔ 하위 iframe 간 내부 postMessage 프로토콜 */
export const SYNAPSE_FRAME_EXTRACT_REQUEST = 'SYNAPSE_FRAME_EXTRACT_REQUEST' as const
export const SYNAPSE_FRAME_EXTRACT_RESPONSE = 'SYNAPSE_FRAME_EXTRACT_RESPONSE' as const

export interface ExtractPageTextRequest {
  type: typeof SYNAPSE_EXTRACT_PAGE_TEXT
}

export interface ExtractPageTextResponse {
  body: string
}

export interface FrameExtractRequest {
  type: typeof SYNAPSE_FRAME_EXTRACT_REQUEST
}

export interface FrameExtractResponse {
  type: typeof SYNAPSE_FRAME_EXTRACT_RESPONSE
  body: string
}

export function isExtractPageTextRequest(
  message: unknown,
): message is ExtractPageTextRequest {
  if (!message || typeof message !== 'object') return false
  return (message as ExtractPageTextRequest).type === SYNAPSE_EXTRACT_PAGE_TEXT
}

export function isFrameExtractRequest(data: unknown): data is FrameExtractRequest {
  if (!data || typeof data !== 'object') return false
  return (data as FrameExtractRequest).type === SYNAPSE_FRAME_EXTRACT_REQUEST
}

export function isFrameExtractResponse(data: unknown): data is FrameExtractResponse {
  if (!data || typeof data !== 'object') return false
  return (data as FrameExtractResponse).type === SYNAPSE_FRAME_EXTRACT_RESPONSE
}
