/**
 * Archiver 엔진 단일 진입점 — Chat UI는 이 훅만 import한다.
 * 탭 컨텍스트 구독 · 히스토리 로드 · 1차/2차 DOM 스트리밍을 내부에서 처리한다.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  resolveArchiverSessionForContext,
  streamArchiverMessage,
  type ArchiverStreamEventPayload,
  type ArchiverStreamEventType,
} from '@/features/archiver/services/archiverClient'
import type {
  ArchiverChatMessage,
  TabContext,
} from '@/features/archiver/models/types'
import {
  queryActiveTabContext,
  queryActiveTabContextForSend,
} from '@/features/archiver/services/queryTabContext'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export type {
  ArchiverStreamEventPayload,
  ArchiverStreamEventType,
  ArchiverStreamStatus,
} from '@/features/archiver/services/archiverClient'

export function useArchiver() {
  const [currentContext, setCurrentContext] = useState<TabContext | null>(null)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [serverHistory, setServerHistory] = useState<ArchiverChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isSessionLoading, setIsSessionLoading] = useState(false)

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

    let cancelled = false

    if (!currentContext) {
      void Promise.resolve().then(() => {
        if (cancelled) return
        setCurrentSessionId(null)
        setServerHistory([])
        setIsSessionLoading(false)
      })
      return () => {
        cancelled = true
      }
    }

    void Promise.resolve().then(() => {
      if (cancelled) return
      setIsSessionLoading(true)
    })

    void resolveArchiverSessionForContext(currentContext)
      .then(({ sessionId, history }) => {
        if (cancelled) return
        setCurrentSessionId(sessionId)
        setServerHistory(history)
      })
      .catch((error) => {
        if (cancelled) return
        console.error('[Synapse Archiver] 히스토리 로드 실패:', error)
        setCurrentSessionId(null)
        setServerHistory([])
      })
      .finally(() => {
        if (!cancelled) setIsSessionLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [currentContext, isStreaming])

  const streamMessage = useCallback(
    async (
      message: string,
      onEvent: (event: ArchiverStreamEventType, payload: ArchiverStreamEventPayload) => void,
    ): Promise<string> => {
      setIsStreaming(true)
      try {
        const contextAtSend = await queryActiveTabContext()
        setCurrentContext(contextAtSend)

        let result = await streamArchiverMessage({
          message,
          context: contextAtSend,
          onEvent,
        })

        if (result.needsDom) {
          const contextWithBody = await queryActiveTabContextForSend()
          setCurrentContext(contextWithBody)

          result = await streamArchiverMessage({
            message,
            context: contextWithBody,
            domContinuation: true,
            onEvent,
          })
        }

        return result.finalContent
      } finally {
        setIsStreaming(false)
      }
    },
    [],
  )

  return {
    currentContext,
    currentSessionId,
    serverHistory,
    isStreaming,
    isSessionLoading,
    streamMessage,
  }
}
