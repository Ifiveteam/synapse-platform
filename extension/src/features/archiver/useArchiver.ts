/**
 * Archiver 엔진 단일 진입점 — Chat UI는 이 훅만 import한다.
 * 탭 컨텍스트 구독 · 히스토리 로드 · 1차/2차 DOM 스트리밍을 내부에서 처리한다.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  fetchHistoryForContext,
  type ArchiverChatMessage,
} from '@/features/archiver/services/archiverApi'
import { sendArchiverMessageWithDomFallback } from '@/features/archiver/services/archiverSend'
import {
  queryActiveTabContext,
  type TabContext,
} from '@/features/archiver/services/tabContext'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export type { TabContext, ArchiverChatMessage }

export function useArchiver() {
  const [currentContext, setCurrentContext] = useState<TabContext | null>(null)
  const [serverHistory, setServerHistory] = useState<ArchiverChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

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
    if (isStreaming) return

    if (!currentContext) {
      setServerHistory([])
      return
    }

    let cancelled = false

    void fetchHistoryForContext(currentContext)
      .then((history) => {
        if (cancelled) return
        setServerHistory(history)
      })
      .catch((error) => {
        if (cancelled) return
        console.error('[Synapse Archiver] 히스토리 로드 실패:', error)
        setServerHistory([])
      })

    return () => {
      cancelled = true
    }
  }, [currentContext, isStreaming])

  const streamMessage = useCallback(
    async (message: string, onChunk: (displayText: string) => void): Promise<string> => {
      setIsStreaming(true)
      try {
        const result = await sendArchiverMessageWithDomFallback({
          message,
          onChunk,
          onContextChange: setCurrentContext,
        })
        return result.finalContent
      } finally {
        setIsStreaming(false)
      }
    },
    [],
  )

  return {
    currentContext,
    serverHistory,
    isStreaming,
    streamMessage,
  }
}
