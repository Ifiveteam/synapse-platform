/**
 * 익스텐션 리로드·HMR 후에도 페이지에 남은 content script가
 * chrome API를 호출하면 "Extension context invalidated"가 throw된다.
 * 접근 전 try/catch로 컨텍스트 유효성을 검사한다.
 */
export function isExtensionContextValid(): boolean {
  try {
    return typeof chrome !== 'undefined' && !!chrome.runtime?.id
  } catch {
    return false
  }
}
