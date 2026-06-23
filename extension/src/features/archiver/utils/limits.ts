// 🔥 WARNING: BACKEND SSOT SYNC REQUIRED (constants.py / context_body_quality.py)
/**
 * 이 파일의 한도·품질 상수는 backend `app/agents/archiver/constants.py` 와
 * 반드시 동기화해야 합니다. 백엔드 값 변경 시 여기도 함께 수정하세요.
 *
 * 대응 관계:
 * - MAX_TAB_CONTEXT_BODY_CHARS  ↔  MAX_CONTEXT_BODY_CHARS
 * - MIN_TAB_CONTEXT_BODY_CHARS  ↔  MIN_CLIENT_CONTEXT_BODY_CHARS
 * - MIN_CONTEXT_BODY_QUALITY    ↔  MIN_CONTEXT_BODY_QUALITY
 * - DOM_* 상수                  ↔  (익스텐션 전용 — content script 추출 타이밍)
 */

/** backend MAX_CONTEXT_BODY_CHARS 와 동일 */
export const MAX_TAB_CONTEXT_BODY_CHARS = 5_000

/** 이보다 짧으면 DOM 추출 실패로 간주 — backend MIN_CLIENT_CONTEXT_BODY_CHARS 와 동일 */
export const MIN_TAB_CONTEXT_BODY_CHARS = 80

/** backend MIN_CONTEXT_BODY_QUALITY 와 동일 */
export const MIN_CONTEXT_BODY_QUALITY = 0.35

/** MutationObserver — DOM 변경이 멈춘 뒤 추가 대기(ms) */
export const DOM_STABILITY_QUIET_MS = 350

/** MutationObserver — 최대 대기 시간(ms) */
export const DOM_STABILITY_MAX_WAIT_MS = 2_500

/** 안정화 대기 중 스냅샷 디바운스(ms) */
export const DOM_SNAPSHOT_DEBOUNCE_MS = 120

/** 안정화 이후 2차 스냅샷 대기(ms) */
export const DOM_SNAPSHOT_DELAY_MS = 400

/** 탭별 DOM 본문 캐시 유효기간(ms) — 동일 탭·URL 연속 질문 시 재추출 생략 */
export const DOM_CACHE_TTL_MS = 45_000
