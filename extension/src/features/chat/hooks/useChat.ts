import { useEffect, useRef, useState } from 'react'
import {
  useArchiver,
  type ArchiverStreamEventPayload,
  type ArchiverStreamEventType,
  type ArchiverStreamStatus,
} from '@/features/archiver/useArchiver'
import type { ArchiverChatMessage } from '@/features/archiver/models/types'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

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

function normalizeStatusPayload(payload: ArchiverStreamEventPayload): ArchiverStreamStatus {
  if (typeof payload === 'string') {
    return payload.trim()
  }
  return payload
}

/** 사이드패널 채팅 UI — 렌더링·메시지 슬롯 관리만 담당. 엔진 로직은 useArchiver에 위임. */
export function useChat() {
  const { currentContext, serverHistory, isStreaming, streamMessage } = useArchiver()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentStatus, setCurrentStatus] = useState<ArchiverStreamStatus | null>(null)
  const scrollAnchorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isStreaming) return
    setMessages(historyToChatMessages(serverHistory))
    setCurrentStatus(null)
  }, [serverHistory, isStreaming])

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentStatus])

  const sendMessage = async (userText: string) => {
    if (!userText.trim() || isStreaming) return

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
    isGenerating: isStreaming,
    sendMessage,
    scrollAnchorRef,
  }
}
