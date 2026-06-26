/**
 * Archiver API 계약 타입 — 익스텐션 내부 SSOT.
 *
 * 백엔드 `app/schemas/archiver.py`와 수동 동기화한다.
 * 스키마 변경 시 이 파일을 직접 갱신한다.
 */

/** DOM 추출 결과 요약 — 캐시 hit 여부·본문 길이 */
export interface TabContextExtractionMeta {
  /** 추출·캐시된 본문 글자 수 */
  char_count: number
  /** 익스텐션 DOM 캐시에서 재사용된 본문인지 여부 */
  is_cached?: boolean
}

/** `TabContextMeta.page_kind` 허용 값 */
export type TabContextPageKind = 'default' | 'map'

/** SPA·사이트별 라우팅 힌트 — 익스텐션이 URL·추출 맥락에서 채운다 */
export interface TabContextMeta {
  /** 활성 탭 URL 호스트명 */
  hostname: string
  /** 페이지 유형 힌트 (지도 SPA 등 전용 크롤러 라우팅용) */
  page_kind?: TabContextPageKind | null
  /** DOM 본문 추출 메타 (2차 요청·need_dom 이후에만 채워짐) */
  extraction?: TabContextExtractionMeta | null
}

/** 활성 탭 맥락 — POST /archiver/stream `context` */
export interface TabContext {
  url: string
  title: string
  /** 익스텐션 content script가 추출한 활성 탭 가시 DOM 텍스트 (최대 5000자) */
  body?: string | null
  /** 호스트·페이지 유형·추출 메타 (하위 호환 optional) */
  meta?: TabContextMeta | null
}

/** 익스텐션 사이드패널 → 아카이버 스트림 요청 본문 */
export interface ChatStreamRequest {
  /** 사용자 질문 또는 지시 */
  message: string
  /** 활성 탭 맥락 (URL, 제목, 선택적 DOM 본문) */
  context?: TabContext | null
  /** NEED_DOM 이후 DOM 본문을 실어 보내는 2차 요청 여부 */
  dom_continuation?: boolean
}

/** GET /archiver/sessions 응답 항목 */
export interface ArchiverSessionSummary {
  session_id: string
  context_title: string
  context_url: string
  last_activity: string
}

/** GET /archiver/history/{session_id} 응답 항목 */
export interface ArchiverChatMessage {
  id: number
  role: string
  content: string
  created_at: string
}

/** SSE status 구조화 필드 — backend `protocols/stream_status.py` 와 수동 동기화 */
export type ArchiverStatusPhase =
  | 'router_general'
  | 'router_parallel'
  | 'collect'
  | 'rag'
  | 'search'
  | 'evaluator'
  | 'respond'
  | 'need_dom'

export interface ArchiverStructuredStatus {
  message: string
  phase?: ArchiverStatusPhase
  engines?: string[]
}

/** 스트리밍 UI 상태 — 레거시 문자열 또는 구조화 payload */
export type ArchiverStreamStatus = string | ArchiverStructuredStatus
