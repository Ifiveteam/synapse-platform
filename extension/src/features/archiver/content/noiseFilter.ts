/**
 * DOM 노이즈·가시성 필터.
 *
 * 역할: 본문이 아닌 DOM을 수집 대상에서 제외한다.
 * 하는 일:
 * - Synapse 익스텐션 UI host 제외
 * - script/style/svg 등 노이즈 태그 판별·일괄 제거
 * - display:none, aria-hidden 등 절대 비가시 요소 제외 (뷰포트 밖 off-screen은 허용)
 */
import { NOISE_SELECTORS, NOISE_TAGS, SYNAPSE_HOST_ROOT_ID } from './constants'

export function isSynapseHost(element: Element): boolean {
  return element.id === SYNAPSE_HOST_ROOT_ID
}

export function isNoiseElement(element: Element): boolean {
  return NOISE_TAGS.has(element.tagName)
}

function isAbsolutelyHidden(element: HTMLElement, style: CSSStyleDeclaration): boolean {
  if (style.display === 'none') return true
  if (style.visibility === 'hidden' || style.visibility === 'collapse') return true
  if (parseFloat(style.opacity) === 0) return true
  if (style.contentVisibility === 'hidden') return true
  if (element.getAttribute('aria-hidden') === 'true') return true
  return false
}

/**
 * 절대적 비가시성만 거른다.
 * 스크롤 컨테이너·뷰포트 밖(off-screen) 리스트 아이템은 좌표와 무관하게 수집한다.
 */
export function isElementVisible(element: HTMLElement): boolean {
  try {
    if (!element.isConnected) return false
    if (isSynapseHost(element)) return false

    const style = window.getComputedStyle(element)
    if (isAbsolutelyHidden(element, style)) return false

    // 레이아웃 박스가 전혀 없는 노드만 제외 (뷰포트 밖 위치는 허용)
    if (element.offsetWidth === 0 && element.offsetHeight === 0) {
      const hasText = (element.textContent?.trim().length ?? 0) > 0
      const hasChildElement = element.querySelector('*') !== null
      if (!hasText && !hasChildElement) return false
    }

    return true
  } catch {
    return false
  }
}

export function stripNoiseElements(root: ParentNode): void {
  try {
    NOISE_SELECTORS.forEach((selector) => {
      root.querySelectorAll(selector).forEach((node) => {
        try {
          node.remove()
        } catch {
          // ignore per-node removal failure
        }
      })
    })
  } catch {
    // ignore
  }
}
