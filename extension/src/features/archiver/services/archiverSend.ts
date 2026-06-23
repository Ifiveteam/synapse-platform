/**
 * Archiver 메시지 전송 — 1차(URL·제목) / 2차(need_dom DOM 수집) SSE 오케스트레이션.
 */

import { streamArchiverMessage } from '@/features/archiver/services/archiverApi'
import {
  queryActiveTabContext,
  queryActiveTabContextForSend,
  type TabContext,
} from '@/features/archiver/services/tabContext'

export interface ArchiverSendOptions {
  message: string
  onChunk: (displayContent: string) => void
  onContextChange?: (context: TabContext | null) => void
}

export interface ArchiverSendResult {
  finalContent: string
  context: TabContext | null
}

/**
 * 1차 스트림 후 need_dom 이벤트가 오면 DOM 본문을 수집해 2차 스트림을 이어 붙인다.
 */
export async function sendArchiverMessageWithDomFallback(
  options: ArchiverSendOptions,
): Promise<ArchiverSendResult> {
  const { message, onChunk, onContextChange } = options

  const contextAtSend = await queryActiveTabContext()
  onContextChange?.(contextAtSend)

  let result = await streamArchiverMessage({
    message,
    context: contextAtSend,
    onChunk,
  })

  let finalContext = contextAtSend

  if (result.needsDom) {
    const contextWithBody = await queryActiveTabContextForSend()
    finalContext = contextWithBody
    onContextChange?.(contextWithBody)

    result = await streamArchiverMessage({
      message,
      context: contextWithBody,
      domContinuation: true,
      onChunk,
    })
  }

  return {
    finalContent: result.finalContent,
    context: finalContext,
  }
}
