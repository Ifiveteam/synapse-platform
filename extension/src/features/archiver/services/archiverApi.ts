import type { TabContext } from '@/features/archiver/services/tabContext'
import { API_BASE } from '@/shared/api/config'
import { getAuthHeaders } from '@/shared/api/client'

// ── SSE 파싱 ────────────────────────────────────────────────────────────────

type ArchiverStreamEventType = 'status' | 'token' | 'need_dom'

interface ArchiverStreamChunk {
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
      if (name === 'status' || name === 'token' || name === 'need_dom') {
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

function parseArchiverSseBuffer(buffer: string): ParseResult {
  const parts = buffer.split('\n\n')
  const remainder = parts.pop() ?? ''
  const events: ArchiverStreamChunk[] = []

  for (const part of parts) {
    const chunk = parseSseBlock(part.trim())
    if (chunk) events.push(chunk)
  }

  return { events, remainder }
}

function joinTokenContent(events: ArchiverStreamChunk[]): string {
  return events
    .filter((item) => item.event === 'token')
    .map((item) => item.content)
    .join('')
}

function joinDisplayContent(events: ArchiverStreamChunk[]): string {
  const tokenContent = joinTokenContent(events)
  if (tokenContent) return tokenContent

  const statusEvents = events.filter(
    (item) => item.event === 'status' || item.event === 'need_dom',
  )
  if (statusEvents.length === 0) return ''

  return statusEvents[statusEvents.length - 1].content
}

// ── HTTP API ────────────────────────────────────────────────────────────────

export interface ArchiverSessionSummary {
  session_id: string
  context_title: string
  context_url: string
  last_activity: string
}

export interface ArchiverChatMessage {
  id: number
  role: string
  content: string
  created_at: string
}

interface ApiListResponse<T> {
  status: string
  data: T[]
}

interface StreamArchiverResult {
  finalContent: string
  needsDom: boolean
}

export async function fetchArchiverSessions(): Promise<ArchiverSessionSummary[]> {
  const response = await fetch(`${API_BASE}/api/v1/archiver/sessions`, {
    headers: await getAuthHeaders(),
  })

  if (!response.ok) {
    throw new Error(`archiver/sessions failed: ${response.status}`)
  }

  const body = (await response.json()) as ApiListResponse<ArchiverSessionSummary>
  return body.data ?? []
}

export async function fetchArchiverHistory(
  sessionId: string,
): Promise<ArchiverChatMessage[]> {
  const response = await fetch(`${API_BASE}/api/v1/archiver/history/${sessionId}`, {
    headers: await getAuthHeaders(),
  })

  if (!response.ok) {
    throw new Error(`archiver/history failed: ${response.status}`)
  }

  const body = (await response.json()) as ApiListResponse<ArchiverChatMessage>
  return body.data ?? []
}

/** 활성 탭 URL과 일치하는 세션의 대화 히스토리를 조회한다. */
export async function fetchHistoryForContext(
  context: TabContext,
): Promise<ArchiverChatMessage[]> {
  const sessions = await fetchArchiverSessions()
  const session = sessions.find((item) => item.context_url === context.url)
  if (!session) return []
  return fetchArchiverHistory(session.session_id)
}

export async function streamArchiverMessage(options: {
  message: string
  context: TabContext | null
  domContinuation?: boolean
  onChunk: (displayContent: string) => void
}): Promise<StreamArchiverResult> {
  const { message, context, domContinuation = false, onChunk } = options

  const response = await fetch(`${API_BASE}/api/v1/archiver/stream`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ message, context, dom_continuation: domContinuation }),
  })

  if (!response.ok || !response.body) {
    throw new Error('스트리밍 연결 실패')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let sseBuffer = ''
  const streamChunks: ArchiverStreamChunk[] = []

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    sseBuffer += decoder.decode(value, { stream: true })
    const parsed = parseArchiverSseBuffer(sseBuffer)
    sseBuffer = parsed.remainder
    if (parsed.events.length > 0) {
      streamChunks.push(...parsed.events)
      onChunk(joinDisplayContent(streamChunks))
    }
  }

  if (sseBuffer.trim()) {
    const tail = parseArchiverSseBuffer(`${sseBuffer}\n\n`)
    if (tail.events.length > 0) {
      streamChunks.push(...tail.events)
      onChunk(joinDisplayContent(streamChunks))
    }
  }

  return {
    finalContent: joinTokenContent(streamChunks),
    needsDom: streamChunks.some((item) => item.event === 'need_dom'),
  }
}
