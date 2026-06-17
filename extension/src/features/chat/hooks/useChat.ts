import { useEffect, useRef, useState } from 'react'
import { isBlacklisted } from '@/features/tracking/utils/blacklist'
import { API_BASE } from '@/shared/api/client'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface TabContext {
  url: string
  title: string
}

function formatTimestamp() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/** 활성 탭 URL·제목을 패시브 힌트로 조회 — 전송 직전에도 재사용 */
function queryActiveTabContext(): Promise<TabContext | null> {
  return new Promise((resolve) => {
    if (!isExtensionContextValid() || !chrome.tabs) {
      resolve(null)
      return
    }

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError || !tabs[0]?.url) {
        resolve(null)
        return
      }

      const { url, title } = tabs[0]
      if (isBlacklisted(url)) {
        resolve(null)
        return
      }

      resolve({
        url,
        title: title || '제목 없는 페이지',
      })
    })
  })
}

/**
 * 사이드패널 AI 채팅 세션 — 활성 탭 컨텍스트 바인딩과 SSE 스트리밍 응답을 관리한다.
 * ChatInput은 sendMessage만 연결하면 된다.
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
    const handleTabUpdated = (tabId: number, changeInfo: { url?: string; title?: string; status?: string }) => {
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
      // 질문 전송 시점의 활성 탭을 다시 조회해 stale 컨텍스트 전송을 방지
      const contextAtSend = await queryActiveTabContext()
      setCurrentContext(contextAtSend)

      const response = await fetch(`${API_BASE}/api/v1/archiver/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          context: contextAtSend,
        }),
      })

      if (!response.ok || !response.body) throw new Error('스트리밍 연결 실패')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''

      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          timestamp: formatTimestamp(),
        },
      ])

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        assistantContent += decoder.decode(value, { stream: true })

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, content: assistantContent } : msg,
          ),
        )
      }
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
