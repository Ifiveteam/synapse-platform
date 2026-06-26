/**
 * 멀티프레임 DOM 본문 수집.
 *
 * 역할: 탭 내 main + iframe 각각 content script에 추출 요청 후 merge한다.
 * 하는 일:
 * - `webNavigation.getAllFrames`로 frameId 목록 (manifest webNavigation 권한)
 * - frame별 `tabs.sendMessage` → extractPageText 응답
 * - `mergeFrameBodies`로 통합 본문 반환
 *
 * chrome.tabs.sendMessage 기본 동작(첫 응답만) 한계를 webNavigation으로 우회한다.
 */
import { mergeFrameBodies } from '@/features/archiver/content/mergeFrameBodies'
import type { ExtractPageTextResponse } from '@/features/archiver/utils/pageContextProtocol'

import { EXTRACT_MESSAGE } from './constants'

/**
 * chrome.webNavigation.getAllFrames — manifest `webNavigation` 권한 필요.
 * 탭 내 메인·하위 iframe frameId 목록을 반환한다.
 */
function getAllFrameIds(tabId: number): Promise<number[]> {
  return new Promise((resolve) => {
    if (!chrome.webNavigation?.getAllFrames) {
      resolve([0])
      return
    }

    chrome.webNavigation.getAllFrames({ tabId }, (frames) => {
      if (chrome.runtime.lastError || !frames?.length) {
        resolve([0])
        return
      }

      const frameIds = [
        ...new Set(
          frames
            .map((frame) => frame.frameId)
            .filter((frameId): frameId is number => typeof frameId === 'number'),
        ),
      ]

      resolve(frameIds.length > 0 ? frameIds : [0])
    })
  })
}

async function extractTextFromFrame(tabId: number, frameId: number): Promise<string> {
  try {
    const response = (await chrome.tabs.sendMessage(tabId, EXTRACT_MESSAGE, {
      frameId,
    })) as ExtractPageTextResponse | undefined

    return response?.body?.trim() ?? ''
  } catch {
    return ''
  }
}

/** 탭 내 모든 프레임에 개별 추출 요청을 보내 본문을 통합한다. */
export async function extractDomBodyFromTab(tabId: number): Promise<string | null> {
  const frameIds = await getAllFrameIds(tabId)

  const results = await Promise.allSettled(
    frameIds.map((frameId) => extractTextFromFrame(tabId, frameId)),
  )

  const bodies = results
    .filter((result): result is PromiseFulfilledResult<string> => result.status === 'fulfilled')
    .map((result) => result.value)
    .filter((text) => text.length > 0)

  const merged = mergeFrameBodies(bodies)
  return merged || null
}
