/**
 * Archiver 백엔드 클라이언트 — REST 호출·SSE 스트림 구독·이벤트 envelope 파싱 SSOT.
 *
 * 프로토콜: backend `protocols/streaming.py`
 * event: status | token | need_dom
 * data: {"content": "..."} + optional status: phase, engines, message
 */
import type {
  ArchiverChatMessage,
  ArchiverSessionSummary,
  ArchiverStatusPhase,
  ArchiverStreamStatus,
  ArchiverStructuredStatus,
  ChatStreamRequest,
  TabContext,
} from '@/features/archiver/models/types'
import { API_BASE } from '@/shared/api/config'
import { getAuthHeaders } from '@/shared/api/client'

interface ApiListResponse<T> {
  status: string
  data: T[]
}

export type ArchiverStreamEventType = 'status' | 'token' | 'need_dom'

export type { ArchiverStreamStatus, ArchiverStructuredStatus, ArchiverStatusPhase }

interface ArchiverStreamChunk {
  event: ArchiverStreamEventType
  content: string
  statusPayload?: ArchiverStreamStatus
}

export type ArchiverStreamEventPayload = string | ArchiverStreamStatus

type ArchiverStreamEventHandler = (
  event: ArchiverStreamEventType,
  payload: ArchiverStreamEventPayload,
) => void

interface StreamArchiverMessageOptions {
  message: string
  context: TabContext | null
  domContinuation?: boolean
  onEvent: ArchiverStreamEventHandler
}

interface ConsumeArchiverSseResult {
  finalContent: string
  needsDom: boolean
}

const VALID_PHASES = new Set<ArchiverStatusPhase>([
  'router_general',
  'router_parallel',
  'collect',
  'rag',
  'search',
  'evaluator',
  'respond',
  'need_dom',
])

function parseStructuredStatus(
  payload: Record<string, unknown>,
  content: string,
): ArchiverStreamStatus {
  const phaseRaw = payload.phase
  const enginesRaw = payload.engines
  const messageRaw = payload.message

  const hasStructured =
    (typeof phaseRaw === 'string' && VALID_PHASES.has(phaseRaw as ArchiverStatusPhase)) ||
    (Array.isArray(enginesRaw) && enginesRaw.length > 0) ||
    typeof messageRaw === 'string'

  if (!hasStructured) {
    return content
  }

  const engines = Array.isArray(enginesRaw)
    ? enginesRaw.filter((item): item is string => typeof item === 'string')
    : undefined

  const structured: ArchiverStructuredStatus = {
    message: typeof messageRaw === 'string' ? messageRaw : content.trim(),
  }

  if (typeof phaseRaw === 'string' && VALID_PHASES.has(phaseRaw as ArchiverStatusPhase)) {
    structured.phase = phaseRaw as ArchiverStatusPhase
  }
  if (engines && engines.length > 0) {
    structured.engines = engines
  }

  return structured
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
    const payload = JSON.parse(dataLine) as Record<string, unknown>
    if (typeof payload.content !== 'string') return null

    const chunk: ArchiverStreamChunk = { event, content: payload.content }
    if (event === 'status' || event === 'need_dom') {
      chunk.statusPayload = parseStructuredStatus(payload, payload.content)
    }
    return chunk
  } catch {
    return null
  }
}

/** `\n\n` 구분 SSE 버퍼에서 완결된 이벤트 블록을 파싱한다. */
function parseArchiverSseBuffer(buffer: string): {
  events: ArchiverStreamChunk[]
  remainder: string
} {
  const parts = buffer.split('\n\n')
  const remainder = parts.pop() ?? ''
  const events: ArchiverStreamChunk[] = []

  for (const part of parts) {
    const chunk = parseSseBlock(part.trim())
    if (chunk) events.push(chunk)
  }

  return { events, remainder }
}

function accumulateTokenContent(events: ArchiverStreamChunk[]): string {
  return events
    .filter((item) => item.event === 'token')
    .map((item) => item.content)
    .join('')
}

function dispatchParsedEvents(
  events: ArchiverStreamChunk[],
  onEvent: ArchiverStreamEventHandler,
  streamChunks: ArchiverStreamChunk[],
): void {
  for (const chunk of events) {
    streamChunks.push(chunk)
    if (chunk.event === 'token') {
      onEvent(chunk.event, chunk.content)
      continue
    }
    onEvent(chunk.event, chunk.statusPayload ?? chunk.content)
  }
}

async function consumeArchiverSseStream(
  body: ReadableStream<Uint8Array>,
  onEvent: ArchiverStreamEventHandler,
): Promise<ConsumeArchiverSseResult> {
  const reader = body.getReader()
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
      dispatchParsedEvents(parsed.events, onEvent, streamChunks)
    }
  }

  if (sseBuffer.trim()) {
    const tail = parseArchiverSseBuffer(`${sseBuffer}\n\n`)
    if (tail.events.length > 0) {
      dispatchParsedEvents(tail.events, onEvent, streamChunks)
    }
  }

  return {
    finalContent: accumulateTokenContent(streamChunks),
    needsDom: streamChunks.some((item) => item.event === 'need_dom'),
  }
}

async function fetchArchiverSessions(): Promise<ArchiverSessionSummary[]> {
  const response = await fetch(`${API_BASE}/api/v1/archiver/sessions`, {
    headers: await getAuthHeaders(),
  })

  if (!response.ok) {
    throw new Error(`archiver/sessions failed: ${response.status}`)
  }

  const body = (await response.json()) as ApiListResponse<ArchiverSessionSummary>
  return body.data ?? []
}

async function fetchArchiverHistory(
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

export interface ArchiverSessionBundle {
  sessionId: string | null
  history: ArchiverChatMessage[]
}

/** 활성 탭 URL과 일치하는 Archiver 세션 ID·히스토리를 함께 조회한다. */
export async function resolveArchiverSessionForContext(
  context: TabContext,
): Promise<ArchiverSessionBundle> {
  const sessions = await fetchArchiverSessions()
  const session = sessions.find((item) => item.context_url === context.url)
  if (!session) {
    return { sessionId: null, history: [] }
  }

  const history = await fetchArchiverHistory(session.session_id)
  return { sessionId: session.session_id, history }
}

/** 활성 탭 URL과 일치하는 세션의 대화 히스토리를 조회한다. */
export async function fetchHistoryForContext(
  context: TabContext,
): Promise<ArchiverChatMessage[]> {
  const bundle = await resolveArchiverSessionForContext(context)
  return bundle.history
}

/** POST /archiver/stream — SSE 이벤트를 타입별로 구분해 전달한다. */
export async function streamArchiverMessage(
  options: StreamArchiverMessageOptions,
): Promise<ConsumeArchiverSseResult> {
  const { message, context, domContinuation = false, onEvent } = options

  const requestBody: ChatStreamRequest = {
    message,
    context,
    dom_continuation: domContinuation,
  }

  const response = await fetch(`${API_BASE}/api/v1/archiver/stream`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(requestBody),
  })

  if (!response.ok || !response.body) {
    throw new Error('스트리밍 연결 실패')
  }

  return consumeArchiverSseStream(response.body, onEvent)
}
