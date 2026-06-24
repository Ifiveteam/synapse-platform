import { prepareContextBody } from '@/features/archiver/utils/contextBodyQuality'
import { MAX_TAB_CONTEXT_BODY_CHARS } from '@/features/archiver/utils/limits'

/** 여러 프레임에서 수집한 본문을 중복 제거 후 통합한다. */
export function mergeFrameBodies(bodies: string[]): string {
  const normalized = bodies
    .map((raw) => prepareContextBody(raw) || raw.trim())
    .filter((text) => text.length > 0)
    .sort((a, b) => b.length - a.length)

  const kept: string[] = []
  for (const candidate of normalized) {
    const dominated = kept.some(
      (existing) => existing.length > candidate.length && existing.includes(candidate),
    )
    if (dominated) continue

    const shorterIndex = kept.findIndex(
      (existing) => candidate.length > existing.length && candidate.includes(existing),
    )
    if (shorterIndex >= 0) {
      kept[shorterIndex] = candidate
      continue
    }

    if (!kept.includes(candidate)) {
      kept.push(candidate)
    }
  }

  const merged = kept.join('\n\n')
  if (merged.length <= MAX_TAB_CONTEXT_BODY_CHARS) return merged
  return merged.slice(0, MAX_TAB_CONTEXT_BODY_CHARS)
}
