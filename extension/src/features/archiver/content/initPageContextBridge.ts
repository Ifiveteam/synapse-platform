import { extractVisiblePageText } from '@/features/archiver/content/extractPageText'
import {
  isExtractPageTextRequest,
  type ExtractPageTextResponse,
} from '@/features/archiver/utils/pageContextProtocol'

export function isTopFrame(): boolean {
  try {
    return window === window.top
  } catch {
    return true
  }
}

/**
 * all_frames 주입 환경 — 각 프레임이 자신의 DOM만 추출해 응답한다.
 * 멀티프레임 통합은 sidepanel `tabContext.ts`가 webNavigation.getAllFrames로 담당한다.
 */
export function initPageContextBridge(): void {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!isExtractPageTextRequest(message)) return false

    void extractVisiblePageText({ includeEmbeddedIframes: false }).then((body) => {
      const payload: ExtractPageTextResponse = { body }
      sendResponse(payload)
    })

    return true
  })
}
