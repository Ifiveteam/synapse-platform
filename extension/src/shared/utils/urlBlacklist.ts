/**
 * URL·도메인 수집 차단 필터.
 * 트래킹·채팅 맥락 등 민감 페이지가 DB로 유출되지 않도록 원천 차단한다.
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
 * URL이 수집·맥락 전송 차단 대상인지 판별한다.
 * @returns true — 차단, false — 허용
 */
export function isBlacklisted(url: string | undefined): boolean {
  if (!url) return true

  if (SCHEME_BLACKLIST_PATTERNS.some((pattern) => pattern.test(url))) {
    return true
  }

  try {
    const { hostname } = new URL(url)
    return HOSTNAME_BLACKLIST_PATTERNS.some((pattern) => pattern.test(hostname))
  } catch {
    return true
  }
}
