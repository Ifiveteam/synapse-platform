/**
 * 트래킹 수집 대상에서 제외할 URL·도메인 필터.
 * 정부·금융·브라우저 내부 페이지 등 민감 컨텍스트가 DB로 유출되지 않도록 원천 차단한다.
 */

/** 브라우저 시스템 스킴 — 호스트명 파싱 전 1차 차단 */
const SCHEME_BLACKLIST_PATTERNS: RegExp[] = [
  /^chrome:\/\//,
  /^chrome-extension:\/\//,
  /^about:/,
  /^file:\/\//,
]

/** 호스트명 기준 민감 도메인 — 루트·서브도메인 모두 매칭 */
const HOSTNAME_BLACKLIST_PATTERNS: RegExp[] = [
  /(\.|^)gov\.kr$/i,
  /(\.|^)go\.kr$/i,
  /(\.|^)shinhan\.com$/i,
  /(\.|^)kbstar\.com$/i,
  /(\.|^)wooribank\.com$/i,
  /(\.|^)hanafn\.com$/i,
]

/**
 * URL이 수집 차단 대상인지 판별한다.
 * @returns true — 수집 차단, false — 수집 허용
 */
export function isBlacklisted(url: string | undefined): boolean {
  // URL 미확정 탭·빈 값은 수집하지 않음 (안전 측 차단)
  if (!url) return true

  if (SCHEME_BLACKLIST_PATTERNS.some((pattern) => pattern.test(url))) {
    return true
  }

  try {
    // 경로·쿼리 오탐을 피하기 위해 hostname만 검사
    const { hostname } = new URL(url)
    return HOSTNAME_BLACKLIST_PATTERNS.some((pattern) => pattern.test(hostname))
  } catch {
    // 파싱 불가 URL은 신뢰할 수 없으므로 수집 차단
    return true
  }
}
