/**
 * Content Script·Sidepanel·Background가 공유하는 chrome.storage.local 키 상수.
 * 문자열을 한곳에서 관리해 오타와 키 불일치로 인한 상태 싱크 실패를 방지한다.
 */
export const STORAGE_KEYS = {
  /** FAB·사이드패널 트래킹 스위치 ON/OFF — Background 엔진 가동 트리거 */
  TRACKING_STATUS: 'synapse_tracking_status',

  /** 유저가 패키징한 컨텍스트 스크랩 목록 (로컬 캐시) */
  SCRAP_LIST: 'synapse_scrap_list',

  /** backend JWT access token — Archiver 등 인증 API 호출용 (프론트 로그인과 동기화) */
  ACCESS_TOKEN: 'synapse_access_token',

  /** 프론트 OAuth 로그인 유저 스냅샷 */
  AUTH_USER: 'synapse_auth_user',

  /** 익스텐션 전용 refresh token (웹 httpOnly 쿠키와 분리) */
  REFRESH_TOKEN: 'synapse_extension_refresh_token',
} as const

/** STORAGE_KEYS 값의 유니온 타입 — storage get/set 시 타입 안전성 확보 */
export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS]
