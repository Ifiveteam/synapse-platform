import { useEffect, useRef, useState } from 'react'
import {
  fetchHistoryForContext,
  streamArchiverMessage,
} from '@/shared/api/archiver'
import {
  queryActiveTabContext,
  type TabContext,
} from '@/features/archiver/utils/tabContext'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export type { TabContext }

function formatTimestamp(date?: Date | string) {
  const value = date ? new Date(date) : new Date()
  return value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function historyToChatMessages(history: Awaited<ReturnType<typeof fetchHistoryForContext>>): ChatMessage[] {
  return history.map((item) => ({
    id: String(item.id),
    role: item.role === 'assistant' ? 'assistant' : 'user',
    content: item.content,
    timestamp: formatTimestamp(item.created_at),
  }))
}

/**
 * 사이드패널 AI 채팅 세션 — 활성 탭 컨텍스트 바인딩과 SSE 스트리밍 응답을 관리한다.
 */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentContext, setCurrentContext] = useState<TabContext | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const scrollAnchorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isExtensionContextValid() || !chrome.tabs) return

    const syncContext = () => {
      void queryActiveTabContext().then(setCurrentContext)
    }

    syncContext()

    const handleTabActivated = () => syncContext()
    const handleTabUpdated = (
      tabId: number,
      changeInfo: { url?: string; title?: string; status?: string },
    ) => {
      if (!changeInfo.url && !changeInfo.title && changeInfo.status !== 'complete') return

      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]?.id === tabId) syncContext()
      })
    }

    chrome.tabs.onActivated.addListener(handleTabActivated)
    chrome.tabs.onUpdated.addListener(handleTabUpdated)

    return () => {
      chrome.tabs.onActivated.removeListener(handleTabActivated)
      chrome.tabs.onUpdated.removeListener(handleTabUpdated)
    }
  }, [])

  useEffect(() => {
    if (isGenerating) return

    if (!currentContext) {
      setMessages([])
      return
    }

    let cancelled = false

    void fetchHistoryForContext(currentContext)
      .then((history) => {
        if (cancelled) return
        setMessages(historyToChatMessages(history))
      })
      .catch((error) => {
        if (cancelled) return
        console.error('[Synapse Chat] 히스토리 로드 실패:', error)
        setMessages([])
      })

    return () => {
      cancelled = true
    }
  }, [currentContext, isGenerating])

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (userText: string) => {
    if (!userText.trim() || isGenerating) return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: userText,
      timestamp: formatTimestamp(),
    }

    const assistantMessageId = crypto.randomUUID()
    setMessages((prev) => [...prev, userMessage])
    setIsGenerating(true)

    try {
      const contextAtSend = await queryActiveTabContext()
      setCurrentContext(contextAtSend)

      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          timestamp: formatTimestamp(),
        },
      ])

      const { finalContent } = await streamArchiverMessage({
        message: userText,
        context: contextAtSend,
        onChunk: (displayContent) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, content: displayContent } : msg,
            ),
          )
        },
      })

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, content: finalContent } : msg,
        ),
      )
    } catch (error) {
      console.error('[Synapse Chat] 스트리밍 통신 에러:', error)

      const errorContent = '❌ 백엔드 Synapse 인프라와 통신 중 에러가 발생했습니다.'
      setMessages((prev) => {
        const hasAssistantSlot = prev.some((msg) => msg.id === assistantMessageId)
        if (hasAssistantSlot) {
          return prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, content: errorContent } : msg,
          )
        }

        return [
          ...prev,
          {
            id: assistantMessageId,
            role: 'assistant',
            content: errorContent,
            timestamp: formatTimestamp(),
          },
        ]
      })
    } finally {
      setIsGenerating(false)
    }
  }

  return {
    messages,
    currentContext,
    isGenerating,
    sendMessage,
    scrollAnchorRef,
  }
}
