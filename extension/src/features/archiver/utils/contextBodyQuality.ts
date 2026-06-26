// [SSOT_MANUAL_SYNC] 본문 품질 휴리스틱 — limits.ts 상수를 import합니다.
// 규칙 본문은 backend `app/agents/archiver/utils/context_body_quality.py` 와 수동 동기화하세요.

import {
  MIN_CONTEXT_BODY_QUALITY,
  MIN_TAB_CONTEXT_BODY_CHARS,
} from '@/features/archiver/utils/limits'

const CODE_LINE_RE = /^\s*(var|let|const|function|import|export|@media|@keyframes)\b/

function looksLikeCssSelector(line: string): boolean {
  const stripped = line.trim()
  if (stripped.startsWith('.') || stripped.startsWith('#') || stripped.startsWith('@')) {
    return true
  }
  if (/[\s>+~][.#][\w-]/.test(stripped)) {
    return true
  }
  return /^[\w-]+\s*\{/.test(stripped)
}

function isNoiseLine(line: string): boolean {
  const stripped = line.trim()
  if (stripped.length < 2) return false

  if (stripped.includes('{') && stripped.includes('}')) return true
  if ((stripped.match(/;/g)?.length ?? 0) >= 2 && stripped.includes(':')) return true
  if (looksLikeCssSelector(stripped)) return true
  if (CODE_LINE_RE.test(stripped)) return true

  const nonWs = stripped.replace(/\s/g, '').length
  if (nonWs === 0) return true

  const codeChars = stripped.match(/[{};:]/g)?.length ?? 0
  return codeChars / nonWs > 0.15
}

function filterNoiseLines(text: string): string {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !isNoiseLine(line))
    .join('\n')
}

/** SPA 껍데기(짧은 네비·빈 컨테이너 잔여 텍스트) 패널티 — 0.0~1.0 */
export function scoreLineDensity(text: string): number {
  const lines = text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
  if (lines.length === 0) return 0

  const substantive = lines.filter((line) => line.length >= 12)
  const avgLen = lines.reduce((sum, line) => sum + line.length, 0) / lines.length
  const uniqueRatio = new Set(lines.map((line) => line.toLowerCase())).size / lines.length
  const substantiveRatio = substantive.length / lines.length

  if (lines.length >= 8 && avgLen < 18 && substantiveRatio < 0.35) {
    return 0.15
  }
  if (lines.length >= 15 && uniqueRatio < 0.25 && substantiveRatio < 0.5) {
    return 0.2
  }

  return Math.min(
    1,
    substantiveRatio * 0.5 + uniqueRatio * 0.25 + Math.min(avgLen / 80, 1) * 0.25,
  )
}

export function scoreContextBodyQuality(text: string): number {
  const normalized = text.trim()
  if (!normalized) return 0

  const filtered = filterNoiseLines(normalized)
  if (filtered.length < MIN_TAB_CONTEXT_BODY_CHARS) return 0

  const retention = filtered.length / normalized.length
  let naturalChars = 0
  for (const char of filtered) {
    if (/\s/.test(char) || /[a-zA-Z]/.test(char) || /[\uac00-\ud7a3]/.test(char)) {
      naturalChars += 1
    }
  }
  const naturalRatio = naturalChars / filtered.length
  const braceDensity = (filtered.match(/[{}]/g)?.length ?? 0) / filtered.length
  const lineDensity = scoreLineDensity(filtered)

  const base =
    retention * 0.25 + naturalRatio * 0.45 + Math.max(0, 1 - braceDensity * 20) * 0.15
  return Math.min(1, Math.max(0, base + lineDensity * 0.15))
}

function isMeaningfulContextBody(text: string): boolean {
  const normalized = text.trim()
  if (normalized.length < MIN_TAB_CONTEXT_BODY_CHARS) return false
  if (scoreLineDensity(normalized) < 0.2) return false
  return scoreContextBodyQuality(normalized) >= MIN_CONTEXT_BODY_QUALITY
}

export function prepareContextBody(text: string): string {
  const normalized = text.trim()
  if (!normalized) return ''

  const filtered = filterNoiseLines(normalized)
  const candidate =
    filtered.length >= MIN_TAB_CONTEXT_BODY_CHARS ? filtered : normalized

  if (!isMeaningfulContextBody(candidate)) return ''
  return candidate
}
