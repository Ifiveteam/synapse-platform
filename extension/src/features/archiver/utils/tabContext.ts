import { isBlacklisted } from '@/shared/utils/urlBlacklist'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export interface TabContext {
  url: string
  title: string
}

/** 활성 탭 URL·제목을 패시브 힌트로 조회 */
export function queryActiveTabContext(): Promise<TabContext | null> {
  return new Promise((resolve) => {
    if (!isExtensionContextValid() || !chrome.tabs) {
      resolve(null)
      return
    }

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError || !tabs[0]?.url) {
        resolve(null)
        return
      }

      const { url, title } = tabs[0]
      if (isBlacklisted(url)) {
        resolve(null)
        return
      }

      resolve({
        url,
        title: title || '제목 없는 페이지',
      })
    })
  })
}
