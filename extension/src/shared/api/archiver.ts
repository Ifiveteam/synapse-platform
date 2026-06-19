import { API_BASE } from '@/shared/api/config'
import { getAuthHeaders } from '@/shared/api/client'
import {
  joinDisplayContent,
  joinTokenContent,
  parseArchiverSseBuffer,
  type ArchiverStreamChunk,
} from '@/shared/api/archiverStream'
import type { TabContext } from '@/features/archiver/utils/tabContext'

export type { TabContext }

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

export interface StreamArchiverOptions {
  message: string
  context: TabContext | null
  onChunk: (displayContent: string, chunks: ArchiverStreamChunk[]) => void
}

export interface StreamArchiverResult {
  finalContent: string
  chunks: ArchiverStreamChunk[]
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

export async function streamArchiverMessage(
  options: StreamArchiverOptions,
): Promise<StreamArchiverResult> {
  const { message, context, onChunk } = options

  const response = await fetch(`${API_BASE}/api/v1/archiver/stream`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ message, context }),
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
      onChunk(joinDisplayContent(streamChunks), streamChunks)
    }
  }

  if (sseBuffer.trim()) {
    const tail = parseArchiverSseBuffer(`${sseBuffer}\n\n`)
    if (tail.events.length > 0) {
      streamChunks.push(...tail.events)
      onChunk(joinDisplayContent(streamChunks), streamChunks)
    }
  }

  return {
    finalContent: joinTokenContent(streamChunks),
    chunks: streamChunks,
  }
}
