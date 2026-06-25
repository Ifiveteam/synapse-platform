/**
 * 추출 문자열 정규화.
 *
 * 역할: raw DOM 텍스트 → Archiver TabContext body로 쓸 수 있는 형태로 다듬는다.
 * 하는 일:
 * - 줄 단위 trim·빈 줄 제거 (`normalizePageText`)
 * - 백엔드 limits 상한으로 자르기 (`truncatePageText`)
 * - `prepareContextBody` 연동 후보 인정 (`normalizeCandidate`)
 */
import {
  prepareContextBody,
  scoreContextBodyQuality,
} from '@/features/archiver/utils/contextBodyQuality'
import {
  MAX_TAB_CONTEXT_BODY_CHARS,
  MIN_TAB_CONTEXT_BODY_CHARS,
} from '@/features/archiver/utils/limits'

export function normalizePageText(raw: string): string {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join('\n')
}

export function truncatePageText(text: string): string {
  if (text.length <= MAX_TAB_CONTEXT_BODY_CHARS) return text
  return text.slice(0, MAX_TAB_CONTEXT_BODY_CHARS)
}

export function normalizeCandidate(raw: string): string {
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
