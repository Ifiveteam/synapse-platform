import { useCallback, useEffect, useRef, useState } from 'react'
import {
  useArchiver,
  type ArchiverStreamEventPayload,
  type ArchiverStreamEventType,
  type ArchiverStreamStatus,
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

const SCRAP_PROCESSING_MESSAGE =
  '[System] 현재 대화 맥락을 요약하여 스크랩 저장소에 등록 중입니다...'
const SCRAP_SUCCESS_MESSAGE = '✓ 스크랩 저장이 완료되었습니다!'
const SCRAP_NO_SESSION_MESSAGE =
  '❌ 현재 페이지와 연결된 대화 세션이 없습니다. 먼저 AI와 대화를 나눠 주세요.'
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

function hasScrapableAssistantTurn(history: ArchiverChatMessage[]): boolean {
  return history.some(
    (item) => item.role === 'assistant' && item.content.trim().length > 0,
  )
}

function normalizeStatusPayload(payload: ArchiverStreamEventPayload): ArchiverStreamStatus {
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

/** 사이드패널 채팅 UI — 렌더링·메시지 슬롯 관리만 담당. 엔진 로직은 useArchiver에 위임. */
export function useChat() {
  const {
    currentContext,
    currentSessionId,
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

  const isBusy = isStreaming || isScraping || isSessionLoading
  const canScrapConversation =
    Boolean(currentSessionId?.trim()) &&
    !isSessionLoading &&
    !isStreaming &&
    hasScrapableAssistantTurn(serverHistory)

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

  const executeChatScrap = useCallback(
    async (options?: { includeUserMessage?: string }) => {
      if (isBusy) return

      const sessionId = currentSessionId?.trim()
      if (!sessionId || !hasScrapableAssistantTurn(serverHistory)) {
        setMessages((prev) => [...prev, createSystemMessage(SCRAP_NO_SESSION_MESSAGE)])
        return
      }

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
          content: SCRAP_PROCESSING_MESSAGE,
          timestamp: formatTimestamp(),
        })
        return next
      })

      try {
        await createScrap({
          source_type: 'chat',
          session_id: sessionId,
          url: currentContext?.url ?? null,
          title: currentContext?.title ?? null,
        })

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === systemMessageId
              ? { ...msg, content: SCRAP_SUCCESS_MESSAGE, timestamp: formatTimestamp() }
              : msg,
          ),
        )
      } catch (error) {
        console.error('[Synapse Chat] 스크랩 실패:', error)
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
    [currentContext, currentSessionId, isBusy, serverHistory],
  )

  const scrapCurrentConversation = useCallback(async () => {
    await executeChatScrap()
  }, [executeChatScrap])

  const sendMessage = async (userText: string) => {
    if (!userText.trim() || isBusy) return

    if (isScrapIntentMessage(userText)) {
      await executeChatScrap({ includeUserMessage: userText.trim() })
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
      if (event === 'status' || event === 'need_dom') {
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
      const finalContent = await streamMessage(userText, onEvent)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, content: finalContent } : msg,
        ),
      )
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
    }
  }

  return {
    messages,
    currentContext,
    currentStatus,
    isGenerating: isBusy,
    isScraping,
    isSessionLoading,
    canScrapConversation,
    sendMessage,
    scrapCurrentConversation,
    scrollAnchorRef,
  }
}
