/**
 * 채팅 입력에서 스크랩 요청 intent를 감지한다.
 */

const SCRAP_INTENT_PATTERNS = [
  /^스크랩\s*해\s*줘[!.?]*$/iu,
  /^저장\s*해\s*줘[!.?]*$/iu,
  /^내용\s*저장[!.?]*$/iu,
  /^스크랩[!.?]*$/iu,
] as const

const SCRAP_INTENT_COMPACT = new Set([
  '스크랩해줘',
  '저장해줘',
  '내용저장',
  '스크랩',
])

/** 유저 메시지가 스크랩 저장 요청인지 판별한다. */
export function isScrapIntentMessage(text: string): boolean {
  const normalized = text.trim()
  if (!normalized) return false

  const compact = normalized.replace(/\s+/g, '').toLowerCase()
  if (SCRAP_INTENT_COMPACT.has(compact)) return true

  return SCRAP_INTENT_PATTERNS.some((pattern) => pattern.test(normalized))
}
