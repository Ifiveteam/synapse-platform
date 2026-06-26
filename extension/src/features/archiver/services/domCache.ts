/**
 * 탭별 DOM 본문 TTL 캐시.
 *
 * 역할: 동일 tabId·URL에서 반복 DOM 추출을 줄인다 (TTL: limits.DOM_CACHE_TTL_MS).
 * 하는 일:
 * - UTM 등 트래킹 쿼리 제거 후 캐시 키 정규화 (백엔드 clean_context_url과 동일 규칙)
 * - get/set + 탭 URL 변경·로딩·닫힘 시 invalidation 리스너
 */
import { DOM_CACHE_TTL_MS } from '@/features/archiver/utils/limits'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

import { TRACKING_QUERY_KEYS } from './constants'

interface DomCacheEntry {
  tabId: number
  url: string
  body: string | null
  extractedAt: number
}

/** 탭별 DOM 본문 캐시 — key: `${tabId}:${normalizedUrl}` */
const domCache = new Map<string, DomCacheEntry>()

let domCacheListenersRegistered = false

/**
 * 백엔드 clean_context_url과 동일 규칙 — 캐시 키·UTM-only 변경 시 false hit 방지.
 */
function normalizeCacheUrl(url: string): string {
  try {
    const parsed = new URL(url)
    const filtered = new URLSearchParams()

    parsed.searchParams.forEach((value, key) => {
      const lower = key.toLowerCase()
      if (TRACKING_QUERY_KEYS.has(lower) || lower.startsWith('utm_')) return
      filtered.append(key, value)
    })

    const path = parsed.pathname.replace(/\/$/, '') || '/'
    const query = filtered.toString()
    return `${parsed.protocol}//${parsed.host}${path}${query ? `?${query}` : ''}`
  } catch {
    return url
  }
}

function buildDomCacheKey(tabId: number, url: string): string {
  return `${tabId}:${normalizeCacheUrl(url)}`
}

function invalidateDomCacheForTab(tabId: number): void {
  const prefix = `${tabId}:`
  for (const key of domCache.keys()) {
    if (key.startsWith(prefix)) {
      domCache.delete(key)
    }
  }
}

/**
 * 탭 URL 변경·새로고침·탭 닫힘 시 해당 탭 캐시를 제거한다.
 * sidepanel에서 tabContext 최초 사용 시 1회 등록.
 */
export function ensureDomCacheListeners(): void {
  if (domCacheListenersRegistered || !isExtensionContextValid() || !chrome.tabs) {
    return
  }

  domCacheListenersRegistered = true

  chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url !== undefined || changeInfo.status === 'loading') {
      invalidateDomCacheForTab(tabId)
    }
  })

  chrome.tabs.onRemoved.addListener((tabId) => {
    invalidateDomCacheForTab(tabId)
  })
}

export function getCachedDomBody(tabId: number, url: string): string | null | undefined {
  const key = buildDomCacheKey(tabId, url)
  const entry = domCache.get(key)
  if (!entry) return undefined

  if (Date.now() - entry.extractedAt >= DOM_CACHE_TTL_MS) {
    domCache.delete(key)
    return undefined
  }

  return entry.body
}

export function setCachedDomBody(tabId: number, url: string, body: string | null): void {
  domCache.set(buildDomCacheKey(tabId, url), {
    tabId,
    url: normalizeCacheUrl(url),
    body,
    extractedAt: Date.now(),
  })
}
