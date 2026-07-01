import { useCallback, useEffect, useRef, useState } from 'react'
import {
  useArchiver,
  type ArchiverStreamEventPayload,
  type ArchiverStreamEventType,
  type ArchiverStreamStatus,
  type ArchiverWebScrapActionPayload,
} from '@/features/archiver/useArchiver'
import type { ArchiverChatMessage } from '@/features/archiver/models/types'
import { createScrap } from '@/features/scrap/services/createScrap'
import { isScrapIntentMessage } from '@/features/chat/utils/scrapIntent'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

const WEB_SCRAP_PROCESSING_MESSAGE =
  '[System] 현재 페이지 본문을 수집하여 스크랩 저장소에 등록 중입니다...'
const SCRAP_SUCCESS_MESSAGE = '✓ 스크랩 저장이 완료되었습니다!'

function scrapSuccessMessage(customCategory?: string | null): string {
  const category = customCategory?.trim()
  if (!category) return SCRAP_SUCCESS_MESSAGE
  return `✓ 「${category}」 카테고리에 스크랩 저장이 완료되었습니다!`
}
const SCRAP_ERROR_MESSAGE = '❌ 스크랩 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.'

function formatTimestamp(date?: Date | string) {
  const value = date ? new Date(date) : new Date()
  return value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function historyToChatMessages(history: ArchiverChatMessage[]): ChatMessage[] {
  return history.map((item) => ({
    id: String(item.id),
    role: item.role === 'assistant' ? 'assistant' : 'user',
    content: item.content,
    timestamp: formatTimestamp(item.created_at),
  }))
}

function isArchiverStreamStatus(
  payload: ArchiverStreamEventPayload,
): payload is ArchiverStreamStatus {
  return typeof payload === 'string' || 'message' in payload
}

function normalizeStatusPayload(payload: ArchiverStreamStatus): ArchiverStreamStatus {
  if (typeof payload === 'string') {
    return payload.trim()
  }
  return payload
}

function createSystemMessage(content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'system',
    content,
    timestamp: formatTimestamp(),
  }
}

function isWebScrapActionPayload(
  payload: ArchiverStreamEventPayload,
): payload is ArchiverWebScrapActionPayload {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    'action' in payload &&
    payload.action === 'TRIGGER_WEB_SCRAP'
  )
}

/** 사이드패널 채팅 UI — 렌더링·메시지 슬롯 관리만 담당. 엔진 로직은 useArchiver에 위임. */
export function useChat() {
  const {
    currentContext,
    serverHistory,
    isStreaming,
    isSessionLoading,
    streamMessage,
  } = useArchiver()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentStatus, setCurrentStatus] = useState<ArchiverStreamStatus | null>(null)
  const [isScraping, setIsScraping] = useState(false)
  const scrollAnchorRef = useRef<HTMLDivElement>(null)
  const contextUrlRef = useRef<string | null>(null)
  const pendingScrapCategoryRef = useRef<string | null>(null)

  const isBusy = isStreaming || isScraping || isSessionLoading
  const canScrapPage = !isBusy

  useEffect(() => {
    const contextUrl = currentContext?.url ?? null
    const contextChanged = contextUrlRef.current !== contextUrl
    contextUrlRef.current = contextUrl

    let cancelled = false

    void Promise.resolve().then(() => {
      if (cancelled) return
      setMessages((prev) => {
        const systemMessages = contextChanged ? [] : prev.filter((msg) => msg.role === 'system')
        return [...historyToChatMessages(serverHistory), ...systemMessages]
      })
      setCurrentStatus(null)
    })

    return () => {
      cancelled = true
    }
  }, [serverHistory, currentContext?.url])

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentStatus])

  const executeWebScrap = useCallback(
    async (options?: { includeUserMessage?: string }) => {
      if (isBusy) return

      const systemMessageId = crypto.randomUUID()
      setIsScraping(true)
      setCurrentStatus(null)

      setMessages((prev) => {
        const next = [...prev]
        if (options?.includeUserMessage) {
          next.push({
            id: crypto.randomUUID(),
            role: 'user',
            content: options.includeUserMessage,
            timestamp: formatTimestamp(),
          })
        }
        next.push({
          id: systemMessageId,
          role: 'system',
          content: WEB_SCRAP_PROCESSING_MESSAGE,
          timestamp: formatTimestamp(),
        })
        return next
      })

      try {
        await createScrap()

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === systemMessageId
              ? { ...msg, content: SCRAP_SUCCESS_MESSAGE, timestamp: formatTimestamp() }
              : msg,
          ),
        )
      } catch (error) {
        console.error('[Synapse Chat] 웹 스크랩 실패:', error)
        const detail = error instanceof Error ? error.message : SCRAP_ERROR_MESSAGE
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === systemMessageId
              ? {
                  ...msg,
                  content: detail.startsWith('❌') ? detail : `❌ ${detail}`,
                  timestamp: formatTimestamp(),
                }
              : msg,
          ),
        )
      } finally {
        setIsScraping(false)
      }
    },
    [isBusy],
  )

  const scrapCurrentPage = useCallback(async () => {
    await executeWebScrap()
  }, [executeWebScrap])

  const sendMessage = async (userText: string) => {
    if (!userText.trim() || isBusy) return

    if (isScrapIntentMessage(userText)) {
      await executeWebScrap({ includeUserMessage: userText.trim() })
      return
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: userText,
      timestamp: formatTimestamp(),
    }

    const assistantMessageId = crypto.randomUUID()
    setCurrentStatus(null)
    setMessages((prev) => [...prev, userMessage])

    const onEvent = (event: ArchiverStreamEventType, payload: ArchiverStreamEventPayload) => {
      if (event === 'action' && isWebScrapActionPayload(payload)) {
        pendingScrapCategoryRef.current = payload.customCategory?.trim() || null
        const categoryHint = pendingScrapCategoryRef.current
          ? `「${pendingScrapCategoryRef.current}」 카테고리에 `
          : ''
        setCurrentStatus(`📌 현재 페이지를 ${categoryHint}스크랩 보관함에 저장하는 중입니다...`)
        return
      }

      if ((event === 'status' || event === 'need_dom') && isArchiverStreamStatus(payload)) {
        setCurrentStatus(normalizeStatusPayload(payload))
        return
      }

      if (event === 'token' && typeof payload === 'string') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, content: msg.content + payload } : msg,
          ),
        )
      }
    }

    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: formatTimestamp(),
      },
    ])

    try {
      const result = await streamMessage(userText, onEvent)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, content: result.finalContent } : msg,
        ),
      )

      if (result.webScrapCompleted) {
        const category =
          result.webScrapCustomCategory ?? pendingScrapCategoryRef.current
        setMessages((prev) => [...prev, createSystemMessage(scrapSuccessMessage(category))])
      }
    } catch (error) {
      console.error('[Synapse Chat] 스트리밍 통신 에러:', error)

      const errorContent = '❌ 백엔드 Synapse 인프라와 통신 중 에러가 발생했습니다.'
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, content: errorContent } : msg,
        ),
      )
    } finally {
      setCurrentStatus(null)
      pendingScrapCategoryRef.current = null
    }
  }

  return {
    messages,
    currentContext,
    currentStatus,
    isGenerating: isBusy,
    isScraping,
    isSessionLoading,
    canScrapPage,
    sendMessage,
    scrapCurrentPage,
    scrollAnchorRef,
  }
}
