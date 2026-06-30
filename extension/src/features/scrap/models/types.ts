/**
 * Scrap API 계약 타입 — 익스텐션 내부 SSOT.
 *
 * 백엔드 `app/schemas/scrap.py`와 수동 동기화한다.
 * 스키마 변경 시 이 파일을 직접 갱신한다.
 */

/** 레거시 DB 레코드 호환용 — 신규 생성은 항상 web */
export type ScrapSourceType = 'web' | 'chat'

/** POST /api/v1/scraps 요청 본문 */
export interface ScrapCreateRequest {
  url?: string | null
  title?: string | null
  raw_body: string
  custom_category?: string | null
}

/** GET/POST /api/v1/scraps 응답 항목 */
export interface ScrapResponse {
  id: string
  user_id: string
  source_type: ScrapSourceType
  url: string | null
  title: string | null
  summary: string
  category: string
  tags: string[]
  raw_body_snapshot: string | null
  session_id: string | null
  created_at: string
  updated_at: string
}

/** 사이드패널 Scrap 카드 UI용 뷰 모델 */
export interface ScrapListItem {
  id: string
  sourceType: ScrapSourceType
  url: string | null
  title: string | null
  summary: string
  category: string
  tags: string[]
  createdAt: string
}

export function toScrapListItem(item: ScrapResponse): ScrapListItem {
  return {
    id: item.id,
    sourceType: item.source_type,
    url: item.url,
    title: item.title,
    summary: item.summary,
    category: item.category,
    tags: item.tags,
    createdAt: item.created_at,
  }
}
