/**
 * 보이는 텍스트 노드 순회 수집.
 *
 * 역할: DOM 트리를 Shadow-safe하게 돌며 가시 텍스트만 모은다.
 * 하는 일:
 * - ShadowRoot는 clone 없이 childNodes만 재귀 탐색
 * - open shadow root host 관통 (`pierceShadow`)
 * - noiseFilter·textNormalize와 연동해 `collectVisibleText` 반환
 */
import { isShadowRoot } from './domSafe'
import { isElementVisible, isNoiseElement, isSynapseHost } from './noiseFilter'
import { normalizePageText } from './textNormalize'

/**
 * Shadow DOM 안전 순회 — ShadowRoot는 절대 clone하지 않고 childNodes만 탐색한다.
 * open shadow root는 host 순회 시 자동으로 관통한다.
 */
function appendVisibleTextFromSubtree(root: Node, parts: string[], pierceShadow: boolean): void {
  if (root.nodeType === Node.TEXT_NODE) {
    const parent = root.parentElement
    if (!parent || isNoiseElement(parent)) return
    if (!(parent instanceof HTMLElement) || !isElementVisible(parent)) return

    const text = root.textContent?.trim()
    if (text) parts.push(text)
    return
  }

  if (isShadowRoot(root)) {
    for (const child of Array.from(root.childNodes)) {
      appendVisibleTextFromSubtree(child, parts, pierceShadow)
    }
    return
  }

  if (root instanceof DocumentFragment) {
    for (const child of Array.from(root.childNodes)) {
      appendVisibleTextFromSubtree(child, parts, pierceShadow)
    }
    return
  }

  if (!(root instanceof HTMLElement)) return
  if (isSynapseHost(root) || isNoiseElement(root)) return

  for (const child of Array.from(root.childNodes)) {
    appendVisibleTextFromSubtree(child, parts, pierceShadow)
  }

  if (pierceShadow && root.shadowRoot) {
    appendVisibleTextFromSubtree(root.shadowRoot, parts, pierceShadow)
  }
}

export function collectVisibleText(root: Node, pierceShadow = true): string {
  const parts: string[] = []
  appendVisibleTextFromSubtree(root, parts, pierceShadow)
  return normalizePageText(parts.join('\n'))
}
