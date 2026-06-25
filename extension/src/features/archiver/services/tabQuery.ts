/**
 * 활성 Chrome 탭 조회.
 *
 * 역할: sidepanel 기준 currentWindow의 active tab URL·제목·tabId를 가져온다.
 * 하는 일:
 * - extension context·blacklist URL 필터
 * - `queryActiveTab` — 내부용 ActiveTabInfo 반환
 */
import { isBlacklisted } from '@/shared/utils/urlBlacklist'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export interface ActiveTabInfo {
  tabId: number
  url: string
  title: string
}

export function queryActiveTab(): Promise<ActiveTabInfo | null> {
  return new Promise((resolve) => {
    if (!isExtensionContextValid() || !chrome.tabs) {
      resolve(null)
      return
    }

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError || !tabs[0]?.id || !tabs[0]?.url) {
        resolve(null)
        return
      }

      const { id, url, title } = tabs[0]
      if (!url || isBlacklisted(url)) {
        resolve(null)
        return
      }

      resolve({
        tabId: id,
        url,
        title: title || '제목 없는 페이지',
      })
    })
  })
}
