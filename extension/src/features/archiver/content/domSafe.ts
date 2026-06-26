/**
 * DOM 조작 방어 유틸.
 *
 * 역할: content script에서 DOM 접근·복제 시 예외가 전체 추출을 중단하지 않게 한다.
 * 하는 일:
 * - ShadowRoot clone 불가 등 복제 가능 노드 판별
 * - `runSafe` — try/catch + debug 로그
 * - `safeCloneSubtree` — body/블록 복제 (ShadowRoot 회피)
 * - `delay` — 스냅샷 간 짧은 대기
 */
/** ShadowRoot는 브라우저 사양상 cloneNode 대상이 아니다. */
export function isShadowRoot(node: Node): node is ShadowRoot {
  return node instanceof ShadowRoot
}

/** 복제 가능한 노드인지 엄격히 검사한다 (ShadowRoot 제외). */
export function canCloneNode(node: Node): boolean {
  if (isShadowRoot(node)) return false
  if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) return true
  if (node.nodeType === Node.ELEMENT_NODE) return true
  return false
}

export function runSafe<T>(label: string, fn: () => T, fallback: T): T {
  try {
    return fn()
  } catch (error) {
    console.debug(`[Synapse extractPageText] ${label} skipped:`, error)
    return fallback
  }
}

export function safeCloneSubtree(node: Node): HTMLElement | DocumentFragment | null {
  if (!canCloneNode(node)) return null
  try {
    const cloned = node.cloneNode(true)
    if (cloned instanceof HTMLElement || cloned instanceof DocumentFragment) {
      return cloned
    }
    return null
  } catch {
    return null
  }
}

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}
