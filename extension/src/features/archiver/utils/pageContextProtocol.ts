/** content script ↔ sidepanel 페이지 본문 추출 메시지 프로토콜 */

export const SYNAPSE_EXTRACT_PAGE_TEXT = 'SYNAPSE_EXTRACT_PAGE_TEXT' as const

export interface ExtractPageTextResponse {
  body: string
}

export function isExtractPageTextRequest(
  message: unknown,
): message is { type: typeof SYNAPSE_EXTRACT_PAGE_TEXT } {
  if (!message || typeof message !== 'object') return false
  return (message as { type: string }).type === SYNAPSE_EXTRACT_PAGE_TEXT
}
