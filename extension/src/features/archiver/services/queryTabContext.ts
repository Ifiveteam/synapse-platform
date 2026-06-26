/**
 * 활성 탭 TabContext 조회 public API.
 *
 * 역할: sidepanel / useArchiver가 쓰는 TabContext 수집 오케스트레이션.
 * 하는 일:
 * - `queryActiveTabContext` — URL·제목·meta만 (1차 요청, DOM 추출 없음)
 * - `queryActiveTabContextForSend` — DOM 추출 + domCache + 멀티프레임 merge (2차·전송용)
 */
import type { TabContext } from '@/features/archiver/models/types'

import { toTabContext } from './contextBuilder'
import {
  ensureDomCacheListeners,
  getCachedDomBody,
  setCachedDomBody,
} from './domCache'
import { extractDomBodyFromTab } from './frameCollect'
import { queryActiveTab } from './tabQuery'

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
