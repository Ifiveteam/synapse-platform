/** 활성 탭 컨텍스트 조회·DOM 캐시·멀티프레임 본문 수집 서비스. */

import { mergeFrameBodies } from '@/features/archiver/content/mergeFrameBodies'
import { DOM_CACHE_TTL_MS } from '@/features/archiver/utils/limits'
import {
  SYNAPSE_EXTRACT_PAGE_TEXT,
  type ExtractPageTextResponse,
} from '@/features/archiver/utils/pageContextProtocol'
import { isBlacklisted } from '@/shared/utils/urlBlacklist'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export type TabContextPageKind = 'default' | 'map'

export interface TabContextExtractionMeta {
  char_count: number
  is_cached: boolean
}

export interface TabContextMeta {
  hostname: string
  page_kind?: TabContextPageKind
  extraction?: TabContextExtractionMeta
}

export interface TabContext {
  url: string
  title: string
  /** content script가 추출한 가시 DOM 텍스트 (전송 시점에만 채움) */
  body?: string | null
  meta?: TabContextMeta
}

interface ActiveTabInfo {
  tabId: number
  url: string
  title: string
}

interface DomCacheEntry {
  tabId: number
  url: string
  body: string | null
  extractedAt: number
}

const EXTRACT_MESSAGE = { type: SYNAPSE_EXTRACT_PAGE_TEXT } as const

/** 탭별 DOM 본문 캐시 — key: `${tabId}:${normalizedUrl}` */
const domCache = new Map<string, DomCacheEntry>()

const TRACKING_QUERY_KEYS = new Set([
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'fbclid',
  'gclid',
  'mc_cid',
  'mc_eid',
  'ref',
  'source',
  'spm',
  'igshid',
])

const MAP_URL_PATTERNS = [
  'naver.com/map',
  'map.naver.com',
  'google.com/maps',
  'maps.google.com',
] as const

let domCacheListenersRegistered = false

function extractHostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return ''
  }
}

/** URL 패턴 기반 페이지 유형 — 백엔드 전용 크롤러 라우팅 힌트 */
export function detectPageKind(url: string): TabContextPageKind {
  const lower = url.toLowerCase()
  if (MAP_URL_PATTERNS.some((pattern) => lower.includes(pattern))) {
    return 'map'
  }
  return 'default'
}

function buildTabContextMeta(
  url: string,
  extraction?: TabContextExtractionMeta,
): TabContextMeta {
  const meta: TabContextMeta = {
    hostname: extractHostnameFromUrl(url),
    page_kind: detectPageKind(url),
  }

  if (extraction) {
    meta.extraction = extraction
  }

  return meta
}

function toTabContext(
  tab: ActiveTabInfo,
  options?: { body?: string | null; isCached?: boolean },
): TabContext {
  const context: TabContext = {
    url: tab.url,
    title: tab.title,
    meta: buildTabContextMeta(
      tab.url,
      options?.body !== undefined
        ? {
            char_count: (options.body ?? '').length,
            is_cached: options.isCached ?? false,
          }
        : undefined,
    ),
  }

  if (options?.body !== undefined) {
    context.body = options.body
  }

  return context
}

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
function ensureDomCacheListeners(): void {
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

function getCachedDomBody(tabId: number, url: string): string | null | undefined {
  const entry = domCache.get(buildDomCacheKey(tabId, url))
  if (!entry) return undefined

  if (Date.now() - entry.extractedAt >= DOM_CACHE_TTL_MS) {
    domCache.delete(buildDomCacheKey(tabId, url))
    return undefined
  }

  return entry.body
}

function setCachedDomBody(tabId: number, url: string, body: string | null): void {
  domCache.set(buildDomCacheKey(tabId, url), {
    tabId,
    url: normalizeCacheUrl(url),
    body,
    extractedAt: Date.now(),
  })
}

function queryActiveTab(): Promise<ActiveTabInfo | null> {
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

/**
 * 탭 내 모든 프레임에 개별 추출 요청을 보내 본문을 통합한다.
 * chrome.tabs.sendMessage 기본 동작(첫 응답만) 한계를 webNavigation으로 우회한다.
 */
async function extractDomBodyFromTab(tabId: number): Promise<string | null> {
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
