/**
 * Archiver content script 진입점 (all_frames).
 *
 * 역할: 각 프레임에서 페이지 본문 추출 메시지 브릿지를 등록한다. React·FAB 없음.
 * 멀티프레임 통합은 sidepanel `frameCollect.ts`가 webNavigation.getAllFrames로 담당한다.
 */
import { extractVisiblePageText } from '@/features/archiver/content/extractVisiblePageText'
import {
  isExtractPageTextRequest,
  type ExtractPageTextResponse,
} from '@/features/archiver/utils/pageContextProtocol'

const BOOT_KEY = '__synapseBootArchiverContent'

function initPageContextBridge(): void {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!isExtractPageTextRequest(message)) return false

    void extractVisiblePageText({ includeEmbeddedIframes: false }).then((body) => {
      const payload: ExtractPageTextResponse = { body }
      sendResponse(payload)
    })

    return true
  })
}

function bootArchiverContentEntry(): void {
  try {
    initPageContextBridge()
  } catch (error) {
    console.error('[Synapse] archiver content script boot 실패:', error)
  }
}

;(globalThis as Record<string, unknown>)[BOOT_KEY] = bootArchiverContentEntry

/** CRXJS 로더 진입점 */
export function onExecute() {
  bootArchiverContentEntry()
}

bootArchiverContentEntry()
