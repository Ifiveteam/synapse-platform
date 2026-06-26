/**
 * TabContext 메타·본문 조립.
 *
 * 역할: 활성 탭 정보 + 추출 결과 → OpenAPI TabContext 객체로 변환한다.
 * 하는 일:
 * - URL hostname·page_kind(meta) 구성
 * - extraction 메타 (char_count, is_cached) 부착
 * - `detectPageKind` — URL 패턴 기반 map/default 분류 (백엔드 라우팅 힌트)
 */
import type {
  TabContext,
  TabContextExtractionMeta,
  TabContextMeta,
  TabContextPageKind,
} from '@/features/archiver/models/types'

import { MAP_URL_PATTERNS } from './constants'
import type { ActiveTabInfo } from './tabQuery'

function extractHostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return ''
  }
}

/** URL 패턴 기반 페이지 유형 — 백엔드 전용 크롤러 라우팅 힌트 */
function detectPageKind(url: string): TabContextPageKind {
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

export function toTabContext(
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
