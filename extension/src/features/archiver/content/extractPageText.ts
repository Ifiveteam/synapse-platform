import {
  prepareContextBody,
  scoreContextBodyQuality,
  scoreLineDensity,
} from '@/features/archiver/utils/contextBodyQuality'
import {
  DOM_SNAPSHOT_DEBOUNCE_MS,
  DOM_SNAPSHOT_DELAY_MS,
  DOM_STABILITY_MAX_WAIT_MS,
  DOM_STABILITY_QUIET_MS,
  MAX_TAB_CONTEXT_BODY_CHARS,
  MIN_TAB_CONTEXT_BODY_CHARS,
} from '@/features/archiver/utils/limits'

const SYNAPSE_HOST_ROOT_ID = 'synapse-extension-root'
const BLOCK_TAGS = new Set(['DIV', 'SECTION', 'ASIDE', 'ARTICLE', 'MAIN'])
const NOISE_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'CANVAS'])

const NOISE_SELECTORS = [
  'script',
  'style',
  'noscript',
  'svg',
  'canvas',
  'iframe',
  'link[rel="stylesheet"]',
]

/** ShadowRoot는 브라우저 사양상 cloneNode 대상이 아니다. */
function isShadowRoot(node: Node): node is ShadowRoot {
  return node instanceof ShadowRoot
}

/** 복제 가능한 노드인지 엄격히 검사한다 (ShadowRoot 제외). */
function canCloneNode(node: Node): boolean {
  if (isShadowRoot(node)) return false
  if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) return true
  if (node.nodeType === Node.ELEMENT_NODE) return true
  return false
}

function runSafe<T>(label: string, fn: () => T, fallback: T): T {
  try {
    return fn()
  } catch (error) {
    console.debug(`[Synapse extractPageText] ${label} skipped:`, error)
    return fallback
  }
}

function safeCloneSubtree(node: Node): HTMLElement | DocumentFragment | null {
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

function normalizePageText(raw: string): string {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join('\n')
}

function truncatePageText(text: string): string {
  if (text.length <= MAX_TAB_CONTEXT_BODY_CHARS) return text
  return text.slice(0, MAX_TAB_CONTEXT_BODY_CHARS)
}

function isSynapseHost(element: Element): boolean {
  return element.id === SYNAPSE_HOST_ROOT_ID
}

function isNoiseElement(element: Element): boolean {
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
function isElementVisible(element: HTMLElement): boolean {
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

function stripNoiseElements(root: ParentNode): void {
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

function countDescendantElements(root: ParentNode): number {
  try {
    return root.querySelectorAll('*').length
  } catch {
    return 0
  }
}

/** 블록·Shadow host의 텍스트 밀도 — SPA 껍데기는 걸러되, 리스트형 대량 텍스트는 보존 */
function scoreBlockTextDensity(
  element: HTMLElement,
  text: string,
  subtreeRoot?: ParentNode,
): number {
  const normalized = normalizePageText(text)
  if (normalized.length < MIN_TAB_CONTEXT_BODY_CHARS) return 0

  const scope = subtreeRoot ?? element
  const childCount = countDescendantElements(scope)
  const charsPerChild = normalized.length / Math.max(1, childCount)
  const lineDensity = scoreLineDensity(normalized)
  const quality = scoreContextBodyQuality(normalized)
  const isSubstantialVolume = normalized.length >= MIN_TAB_CONTEXT_BODY_CHARS * 2

  // 리스트·피드형 — 자식이 많아도 총 텍스트량이 충분하면 후보 유지
  if (!isSubstantialVolume) {
    if (childCount > 40 && charsPerChild < 4) return 0
    if (childCount > 80 && charsPerChild < 8) return 0
  } else if (childCount > 120 && charsPerChild < 1.5) {
    return 0
  }

  let structureFactor = 0.55 + lineDensity * 0.25 + Math.min(charsPerChild / 12, 1) * 0.2

  if (isSubstantialVolume && childCount > 30) {
    const listBoost = Math.min(normalized.length / (MIN_TAB_CONTEXT_BODY_CHARS * 6), 1) * 0.2
    structureFactor = Math.max(structureFactor, 0.5 + listBoost)
  }

  return quality * structureFactor
}

/** 품질·총량·다양성을 균형 평가 — 전역 순회 전략이 단일 블록에 밀리지 않게 */
function scoreExtractionCandidate(text: string): number {
  const normalized = normalizePageText(text)
  if (normalized.length < MIN_TAB_CONTEXT_BODY_CHARS) return 0

  const quality = scoreContextBodyQuality(normalized)
  const lineDensity = scoreLineDensity(normalized)
  const lengthFactor = Math.min(
    normalized.length / (MIN_TAB_CONTEXT_BODY_CHARS * 5),
    1,
  )

  const lines = normalized.split('\n').filter((line) => line.trim().length > 0)
  const diversity =
    lines.length > 0
      ? new Set(lines.map((line) => line.toLowerCase())).size / lines.length
      : 0

  const lineCountFactor = Math.min(lines.length / 40, 1)

  return (
    quality * 0.35 +
    lengthFactor * 0.3 +
    diversity * 0.15 +
    lineDensity * 0.1 +
    lineCountFactor * 0.1
  )
}

function normalizeCandidate(raw: string): string {
  const prepared = prepareContextBody(raw)
  if (prepared) return prepared

  const normalized = normalizePageText(raw)
  if (normalized.length < MIN_TAB_CONTEXT_BODY_CHARS) return ''

  // 리스트형 반복 텍스트 — prepareContextBody가 엄격하게 걸러도 총량이 크면 후보 인정
  if (
    normalized.length >= MIN_TAB_CONTEXT_BODY_CHARS * 2 &&
    scoreContextBodyQuality(normalized) >= 0.28
  ) {
    return normalized
  }

  return ''
}

function pickBest(candidates: string[]): string {
  const ranked = candidates
    .map((raw) => ({ raw, text: normalizeCandidate(raw) }))
    .filter((item) => item.text.length >= MIN_TAB_CONTEXT_BODY_CHARS)
    .sort((a, b) => {
      const scoreDiff = scoreExtractionCandidate(b.text) - scoreExtractionCandidate(a.text)
      if (Math.abs(scoreDiff) > 0.001) return scoreDiff
      return b.text.length - a.text.length
    })

  return ranked[0]?.text ?? ''
}

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

function collectVisibleText(root: Node, pierceShadow = true): string {
  const parts: string[] = []
  appendVisibleTextFromSubtree(root, parts, pierceShadow)
  return normalizePageText(parts.join('\n'))
}

function extractFromCleanedBody(): string {
  const body = document.body
  if (!body) return ''

  const clone = safeCloneSubtree(body)
  if (!clone || !(clone instanceof HTMLElement)) {
    return collectVisibleText(body)
  }

  for (const child of Array.from(clone.children)) {
    if (child instanceof HTMLElement && isSynapseHost(child)) {
      child.remove()
    }
  }
  stripNoiseElements(clone)

  return normalizePageText(clone.innerText || '')
}

function extractFromVisibleTextNodes(root: Node = document.body): string {
  if (!root) return ''
  return collectVisibleText(root, true)
}

function extractFromSemanticRegions(): string {
  const regions: string[] = []

  for (const selector of ['main', '[role="main"]', 'article']) {
    try {
      document.querySelectorAll(selector).forEach((node) => {
        try {
          if (!(node instanceof HTMLElement) || !isElementVisible(node)) return

          const clone = safeCloneSubtree(node)
          let text = ''
          if (clone instanceof HTMLElement) {
            stripNoiseElements(clone)
            text = normalizePageText(clone.innerText || '')
          } else {
            text = collectVisibleText(node, true)
          }

          if (scoreBlockTextDensity(node, text) > 0) {
            regions.push(text)
          }
        } catch {
          // skip region
        }
      })
    } catch {
      // skip selector
    }
  }

  return pickBest(regions)
}

function extractLargestVisibleBlock(): string {
  const blocks: { text: string; score: number }[] = []

  try {
    document.querySelectorAll('div, section, aside, article, main').forEach((node) => {
      try {
        if (!(node instanceof HTMLElement)) return
        if (!isElementVisible(node)) return
        if (!BLOCK_TAGS.has(node.tagName)) return

        const clone = safeCloneSubtree(node)
        let text = ''
        if (clone instanceof HTMLElement) {
          stripNoiseElements(clone)
          text = normalizePageText(clone.innerText || '')
        } else {
          text = collectVisibleText(node, false)
        }

        const density = scoreBlockTextDensity(node, text)
        if (density > 0) {
          blocks.push({ text, score: density + scoreExtractionCandidate(text) * 0.15 })
        }
      } catch {
        // skip block
      }
    })
  } catch {
    // ignore
  }

  blocks.sort((a, b) => b.score - a.score || b.text.length - a.text.length)
  return blocks[0]?.text ?? ''
}

/**
 * open Shadow DOM 전용 추출 — shadowRoot.childNodes를 직접 순회 (clone 금지).
 */
function extractFromOpenShadowRoots(): string {
  const parts: string[] = []

  try {
    document.querySelectorAll('*').forEach((node) => {
      try {
        if (!(node instanceof HTMLElement)) return

        const shadow = node.shadowRoot
        if (!shadow) return
        if (!isElementVisible(node)) return

        const text = collectVisibleText(shadow, true)
        if (text.length < MIN_TAB_CONTEXT_BODY_CHARS || scoreLineDensity(text) < 0.2) {
          return
        }

        const density = scoreBlockTextDensity(node, text, shadow)
        if (density > 0) {
          parts.push(text)
        }
      } catch {
        // skip shadow host
      }
    })
  } catch {
    // ignore
  }

  return pickBest(parts)
}

function extractFromSameOriginIframes(): string {
  const parts: string[] = []

  try {
    document.querySelectorAll('iframe').forEach((frame) => {
      try {
        const doc = frame.contentDocument
        if (!doc?.body) return

        const clone = safeCloneSubtree(doc.body)
        let text = ''
        if (clone instanceof HTMLElement) {
          stripNoiseElements(clone)
          text = normalizePageText(clone.innerText || '')
        } else {
          text = collectVisibleText(doc.body, true)
        }

        if (text.length >= MIN_TAB_CONTEXT_BODY_CHARS && scoreLineDensity(text) >= 0.2) {
          parts.push(text)
        }
      } catch {
        // cross-origin iframe or access denied
      }
    })
  } catch {
    // ignore
  }

  return pickBest(parts)
}

function extractPageTextSnapshot(options: ExtractPageTextOptions = {}): string {
  const includeEmbeddedIframes = options.includeEmbeddedIframes ?? true

  const strategies = [
    () => extractFromCleanedBody(),
    () => extractFromVisibleTextNodes(),
    () => extractFromSemanticRegions(),
    () => extractLargestVisibleBlock(),
    () => extractFromOpenShadowRoots(),
  ]

  if (includeEmbeddedIframes) {
    strategies.push(() => extractFromSameOriginIframes())
  }

  const candidates = strategies
    .map((strategy, index) => runSafe(`strategy-${index}`, strategy, ''))
    .filter((text) => text.length > 0)

  return truncatePageText(pickBest(candidates))
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

interface StabilityOptions {
  quietMs?: number
  maxWaitMs?: number
  onStableTick?: () => void
}

function waitForDomStability(options: StabilityOptions = {}): Promise<void> {
  const quietMs = options.quietMs ?? DOM_STABILITY_QUIET_MS
  const maxWaitMs = options.maxWaitMs ?? DOM_STABILITY_MAX_WAIT_MS
  const root = document.body

  if (!root) {
    return delay(quietMs)
  }

  return new Promise((resolve) => {
    let finished = false
    let quietTimer: number | null = null
    let debounceTimer: number | null = null

    const finish = () => {
      if (finished) return
      finished = true
      observer.disconnect()
      window.clearTimeout(maxTimer)
      if (quietTimer !== null) window.clearTimeout(quietTimer)
      if (debounceTimer !== null) window.clearTimeout(debounceTimer)
      resolve()
    }

    const scheduleQuietFinish = () => {
      if (quietTimer !== null) window.clearTimeout(quietTimer)
      quietTimer = window.setTimeout(finish, quietMs)
    }

    const onMutation = () => {
      if (debounceTimer !== null) window.clearTimeout(debounceTimer)
      debounceTimer = window.setTimeout(() => {
        try {
          options.onStableTick?.()
        } catch {
          // ignore tick failure
        }
      }, DOM_SNAPSHOT_DEBOUNCE_MS)
      scheduleQuietFinish()
    }

    let observer: MutationObserver
    try {
      observer = new MutationObserver(onMutation)
      observer.observe(root, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['class', 'style', 'hidden', 'aria-hidden'],
      })
    } catch {
      resolve()
      return
    }

    const maxTimer = window.setTimeout(finish, maxWaitMs)
    scheduleQuietFinish()
  })
}

function considerSnapshot(
  text: string,
  tracker: { best: string; bestScore: number },
): void {
  try {
    const prepared = normalizeCandidate(text)
    if (!prepared) return

    const score = scoreExtractionCandidate(prepared)
    if (
      score > tracker.bestScore ||
      (score === tracker.bestScore && prepared.length > tracker.best.length)
    ) {
      tracker.best = prepared
      tracker.bestScore = score
    }
  } catch {
    // ignore scoring failure
  }
}

/**
 * 렌더링 안정화 대기 → 다중 스냅샷 중 품질이 가장 높은 가시 텍스트를 반환한다.
 * Shadow DOM은 clone 없이 순회만 하며, 전 구간이 fault-tolerant하다.
 */
export interface ExtractPageTextOptions {
  /** false이면 same-origin iframe DOM 직접 접근 전략을 생략 (all_frames 통합용) */
  includeEmbeddedIframes?: boolean
}

export async function extractVisiblePageText(
  options: ExtractPageTextOptions = {},
): Promise<string> {
  const tracker = { best: '', bestScore: 0 }

  const snapshot = () => {
    considerSnapshot(
      runSafe('snapshot', () => extractPageTextSnapshot(options), ''),
      tracker,
    )
  }

  snapshot()

  try {
    await waitForDomStability({ onStableTick: snapshot })
  } catch {
    // proceed with best effort
  }

  snapshot()
  await delay(DOM_SNAPSHOT_DELAY_MS)
  snapshot()

  if (tracker.best) {
    return truncatePageText(tracker.best)
  }

  return runSafe('final-snapshot', () => extractPageTextSnapshot(options), '')
}
