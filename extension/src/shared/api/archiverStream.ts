export type ArchiverStreamEventType = 'status' | 'token'

export interface ArchiverStreamChunk {
  event: ArchiverStreamEventType
  content: string
}

interface ParseResult {
  events: ArchiverStreamChunk[]
  remainder: string
}

function parseSseBlock(block: string): ArchiverStreamChunk | null {
  const lines = block.split('\n')
  let event: ArchiverStreamEventType | null = null
  let dataLine: string | null = null

  for (const line of lines) {
    if (line.startsWith('event:')) {
      const name = line.slice(6).trim()
      if (name === 'status' || name === 'token') {
        event = name
      }
    } else if (line.startsWith('data:')) {
      dataLine = line.slice(5).trim()
    }
  }

  if (!event || !dataLine) return null

  try {
    const payload = JSON.parse(dataLine) as { content?: string }
    if (typeof payload.content !== 'string') return null
    return { event, content: payload.content }
  } catch {
    return null
  }
}

/** 누적 SSE 버퍼에서 완성된 event/data 프레임을 추출한다. */
export function parseArchiverSseBuffer(buffer: string): ParseResult {
  const parts = buffer.split('\n\n')
  const remainder = parts.pop() ?? ''
  const events: ArchiverStreamChunk[] = []

  for (const part of parts) {
    const chunk = parseSseBlock(part.trim())
    if (chunk) events.push(chunk)
  }

  return { events, remainder }
}

/** token 이벤트만 합쳐 assistant 본문을 만든다. */
export function joinTokenContent(events: ArchiverStreamChunk[]): string {
  return events
    .filter((item) => item.event === 'token')
    .map((item) => item.content)
    .join('')
}

/** 스트리밍 중 UI — token 수신 전 최신 status 하나만, 이후 답변 token만 */
export function joinDisplayContent(events: ArchiverStreamChunk[]): string {
  const tokenContent = joinTokenContent(events)
  if (tokenContent) return tokenContent

  const statusEvents = events.filter((item) => item.event === 'status')
  if (statusEvents.length === 0) return ''

  return statusEvents[statusEvents.length - 1].content
}

