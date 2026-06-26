/**
 * 추출 후보 품질 채점.
 *
 * 역할: 여러 전략·스냅샷이 만든 후보 중 Archiver에 적합한 본문을 고른다.
 * 하는 일:
 * - 블록 텍스트 밀도 (SPA 껍데기 vs 리스트형 본문) — `scoreBlockTextDensity`
 * - 후보 종합 점수 (길이·품질·줄 다양성) — `scoreExtractionCandidate`
 * - 후보 목록·스냅샷 tracker에서 최고점 선택 — `pickBest`, `considerSnapshot`
 */
import {
  scoreContextBodyQuality,
  scoreLineDensity,
} from '@/features/archiver/utils/contextBodyQuality'
import { MIN_TAB_CONTEXT_BODY_CHARS } from '@/features/archiver/utils/limits'

import { normalizeCandidate, normalizePageText } from './textNormalize'

function countDescendantElements(root: ParentNode): number {
  try {
    return root.querySelectorAll('*').length
  } catch {
    return 0
  }
}

/** 블록·Shadow host의 텍스트 밀도 — SPA 껍데기는 걸러되, 리스트형 대량 텍스트는 보존 */
export function scoreBlockTextDensity(
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
export function scoreExtractionCandidate(text: string): number {
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

export function pickBest(candidates: string[]): string {
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

export function considerSnapshot(
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
