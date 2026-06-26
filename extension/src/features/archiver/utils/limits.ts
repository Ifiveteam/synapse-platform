// [SSOT_MANUAL_SYNC] ─────────────────────────────────────────────────────────────
// 루트 shared/ 및 OpenAPI codegen 파이프라인이 제거되었습니다.
// 이 파일이 익스텐션 측 Archiver 상수 SSOT이며, 백엔드와 자동 동기화되지 않습니다.
//
// 아래 [SSOT_SYNC] 표시 상수는 반드시 다음 파일과 값·단위를 수동으로 맞춰 주세요:
//   backend/app/agents/archiver/core/constants.py
//
// 백엔드 상수를 바꿨다면 레포 전체에서 [SSOT_SYNC] 를 검색해 익스텐션도 함께 갱신하세요.
// ┌───────────────────────────────────────────────────────────────── [SSOT_SYNC] ─┐
// │ 매핑 (값·단위 반드시 일치):                                                   │
// │   MAX_BODY_LENGTH / MAX_TAB_CONTEXT_BODY_CHARS  ↔ MAX_BODY_LENGTH            │
// │   QUALITY_THRESHOLD (0–100)                   ↔ QUALITY_THRESHOLD (0–100)  │
// │   MIN_CONTEXT_BODY_QUALITY (0.0–1.0)          ↔ MIN_CONTEXT_BODY_QUALITY     │
// │   DOM_STABILITY_TIMEOUT_MS (ms)                 ↔ DOM_STABILITY_TIMEOUT_MS   │
// │   MIN_TAB_CONTEXT_BODY_CHARS                    ↔ MIN_CLIENT_CONTEXT_BODY_CHARS │
// └──────────────────────────────────────────────────────────────────────────────┘

// ── [SSOT_SYNC] 백엔드 동기화 상수 ──────────────────────────────────────────────

/** 본문 글자 수 최대 제한 — backend MAX_BODY_LENGTH 와 동일 */
export const MAX_BODY_LENGTH = 5_000

/** MAX_BODY_LENGTH alias — mergeFrameBodies·textNormalize 호환 */
export const MAX_TAB_CONTEXT_BODY_CHARS = MAX_BODY_LENGTH

/** 본문 품질 채점 커트라인 (0–100) — backend QUALITY_THRESHOLD 와 동일 */
export const QUALITY_THRESHOLD = 35

/** 0.0–1.0 품질 게이트 — backend MIN_CONTEXT_BODY_QUALITY 와 동일 */
export const MIN_CONTEXT_BODY_QUALITY = QUALITY_THRESHOLD / 100

/** DOM 수집 안정화 quiet 대기 (ms) — backend DOM_STABILITY_TIMEOUT_MS 와 동일 */
export const DOM_STABILITY_TIMEOUT_MS = 500

/** 최소 유효 본문 길이 — backend MIN_CLIENT_CONTEXT_BODY_CHARS 와 동일 */
export const MIN_TAB_CONTEXT_BODY_CHARS = 80

// ── 익스텐션 전용 (content script 추출 타이밍, [SSOT_SYNC] 대상 아님) ─────────

/** DOM_STABILITY_TIMEOUT_MS 호환 alias — domStability.ts 에서 사용 */
export const DOM_STABILITY_QUIET_MS = DOM_STABILITY_TIMEOUT_MS

/** MutationObserver — 최대 대기 시간 (ms) */
export const DOM_STABILITY_MAX_WAIT_MS = 2_500

/** 안정화 대기 중 스냅샷 디바운스 (ms) */
export const DOM_SNAPSHOT_DEBOUNCE_MS = 120

/** 안정화 이후 2차 스냅샷 대기 (ms) */
export const DOM_SNAPSHOT_DELAY_MS = 400

/** 탭별 DOM 본문 캐시 유효기간 (ms) — 동일 탭·URL 연속 질문 시 재추출 생략 */
export const DOM_CACHE_TTL_MS = 45_000
