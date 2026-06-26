/**
 * 다중 추출 전략 + 단일 스냅샷 조합.
 *
 * 역할: 페이지 구조에 따라 여러 방식으로 본문을 수집하고 한 번에 best를 고른다.
 * 하는 일 (6종 전략):
 * - cleaned body innerText
 * - visible text node 순회
 * - main/article 등 시맨틱 영역
 * - largest visible block
 * - open Shadow DOM
 * - same-origin iframe (옵션)
 * - `extractPageTextSnapshot` — 전략 실행 후 `pickBest` + truncate
 */
import { scoreLineDensity } from '@/features/archiver/utils/contextBodyQuality'
import { MIN_TAB_CONTEXT_BODY_CHARS } from '@/features/archiver/utils/limits'

import { BLOCK_TAGS } from './constants'
import { runSafe, safeCloneSubtree } from './domSafe'
import {
  isElementVisible,
  isSynapseHost,
  stripNoiseElements,
} from './noiseFilter'
import {
  pickBest,
  scoreBlockTextDensity,
  scoreExtractionCandidate,
} from './scoring'
import type { ExtractPageTextOptions } from './types'
import { normalizePageText, truncatePageText } from './textNormalize'
import { collectVisibleText } from './visibleText'

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

export function extractPageTextSnapshot(options: ExtractPageTextOptions = {}): string {
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
