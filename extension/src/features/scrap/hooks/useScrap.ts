/**
 * Synapse 스크랩 보관함 — 백엔드 API 동기화 훅.
 */
import { useCallback, useEffect, useState } from 'react'
import { SCRAP_CREATED_MESSAGE } from '@/features/scrap/services/createScrap'
import { deleteScrap as deleteScrapApi, getScraps } from '@/features/scrap/services/scrapClient'
import { type ScrapListItem, toScrapListItem } from '@/features/scrap/models/types'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export type { ScrapListItem }

function mapLoadError(loadError: unknown): string {
  return loadError instanceof Error
    ? loadError.message
    : '스크랩 목록을 불러오지 못했습니다.'
}

export function useScrap() {
  const [scrapList, setScrapList] = useState<ScrapListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reloadScraps = useCallback(() => {
    void getScraps()
      .then((items) => {
        setScrapList(items.map(toScrapListItem))
        setError(null)
      })
      .catch((loadError) => {
        console.error('[Synapse Scrap] 목록 로드 실패:', loadError)
        setScrapList([])
        setError(mapLoadError(loadError))
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  useEffect(() => {
    let cancelled = false

    void getScraps()
      .then((items) => {
        if (cancelled) return
        setScrapList(items.map(toScrapListItem))
        setError(null)
      })
      .catch((loadError) => {
        if (cancelled) return
        console.error('[Synapse Scrap] 목록 로드 실패:', loadError)
        setScrapList([])
        setError(mapLoadError(loadError))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!isExtensionContextValid()) return

    const handleRuntimeMessage = (message: { action?: string }) => {
      if (message.action === SCRAP_CREATED_MESSAGE) {
        reloadScraps()
      }
    }

    chrome.runtime.onMessage.addListener(handleRuntimeMessage)
    return () => {
      chrome.runtime.onMessage.removeListener(handleRuntimeMessage)
    }
  }, [reloadScraps])

  const deleteScrap = useCallback(async (id: string) => {
    setError(null)
    try {
      await deleteScrapApi(id)
      setScrapList((prev) => prev.filter((item) => item.id !== id))
    } catch (deleteError) {
      console.error('[Synapse Scrap] 삭제 실패:', deleteError)
      setError(deleteError instanceof Error ? deleteError.message : '스크랩 삭제에 실패했습니다.')
    }
  }, [])

  return {
    scrapList,
    isLoading,
    error,
    deleteScrap,
  }
}
