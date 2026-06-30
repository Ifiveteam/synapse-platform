/**
 * 활성 탭 TabContext 조회 public API.
 *
 * 역할: sidepanel / useArchiver / FAB(content script)가 쓰는 TabContext 수집 오케스트레이션.
 * 하는 일:
 * - `queryActiveTabContext` — URL·제목·meta만 (1차 요청, DOM 추출 없음)
 * - `queryActiveTabContextForSend` — DOM 추출 + domCache + 멀티프레임 merge (2차·전송용)
 * - content script(FAB)처럼 `chrome.tabs`가 없으면 호스트 페이지에서 직접 추출
 */
import { extractVisiblePageText } from '@/features/archiver/content/extractVisiblePageText'
import type { TabContext } from '@/features/archiver/models/types'
import { isBlacklisted } from '@/shared/utils/urlBlacklist'

import { toTabContext } from './contextBuilder'
import {
  ensureDomCacheListeners,
  getCachedDomBody,
  setCachedDomBody,
} from './domCache'
import { extractDomBodyFromTab } from './frameCollect'
import { hasTabsApi, queryActiveTab, type ActiveTabInfo } from './tabQuery'

/** content script 호스트 페이지 캐시 키용 sentinel (실제 tabId와 충돌하지 않음) */
const HOST_CONTEXT_TAB_ID = -1

async function queryHostPageContextForSend(): Promise<TabContext | null> {
  if (typeof window === 'undefined') return null

  const url = window.location.href
  if (isBlacklisted(url)) return null

  const tab: ActiveTabInfo = {
    tabId: HOST_CONTEXT_TAB_ID,
    url,
    title: document.title?.trim() || '제목 없는 페이지',
  }

  const cachedBody = getCachedDomBody(tab.tabId, tab.url)
  if (cachedBody !== undefined) {
    return toTabContext(tab, { body: cachedBody, isCached: true })
  }

  const body = await extractVisiblePageText({ includeEmbeddedIframes: false })
  setCachedDomBody(tab.tabId, tab.url, body || null)

  return toTabContext(tab, { body, isCached: false })
}

/** 활성 탭 URL·제목 + 라우팅 힌트 meta (DOM 추출 없음 — 1차 요청용) */
export function queryActiveTabContext(): Promise<TabContext | null> {
  return queryActiveTab().then((tab) => {
    if (!tab) return null
    return toTabContext(tab)
  })
}

/**
 * 메시지 전송 직전 — 활성 탭 URL·제목 + 모든 프레임 DOM 본문을 통합 수집한다.
 * 동일 탭·URL에서 TTL(45초) 내 재호출 시 캐시된 body를 즉시 반환한다.
 */
export async function queryActiveTabContextForSend(): Promise<TabContext | null> {
  if (!hasTabsApi()) {
    return queryHostPageContextForSend()
  }

  ensureDomCacheListeners()

  const tab = await queryActiveTab()
  if (!tab) return null

  const cachedBody = getCachedDomBody(tab.tabId, tab.url)
  if (cachedBody !== undefined) {
    return toTabContext(tab, { body: cachedBody, isCached: true })
  }

  const body = await extractDomBodyFromTab(tab.tabId)
  setCachedDomBody(tab.tabId, tab.url, body)

  return toTabContext(tab, { body, isCached: false })
}
