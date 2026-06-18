/**
 * Synapse 컨텍스트 보관함 데이터 동기화 훅
 * chrome.storage.local의 'synapse_scrap_list' 키를 구독하여 실시간 추가/삭제를 UI에 반영합니다.
 */
import { useEffect, useState } from 'react'
import { STORAGE_KEYS } from '@/shared/constants/storageKeys'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export interface ScrapItem {
  id: string
  url: string
  title: string
  scrapedAt: string
}

export function useScrap() {
  const [scrapList, setScrapList] = useState<ScrapItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!isExtensionContextValid() || !chrome.storage?.local) {
      setIsLoading(false)
      return
    }

    // 마운트 시 스토리지에서 기존 스크랩 리스트 로드
    chrome.storage.local.get([STORAGE_KEYS.SCRAP_LIST], (result) => {
      if (chrome.runtime.lastError) return
      const stored = result[STORAGE_KEYS.SCRAP_LIST]
      if (Array.isArray(stored)) {
        setScrapList(stored as ScrapItem[])
      }
      setIsLoading(false)
    })

    // 다른 컨텍스트(FAB 클릭 등)에서 스토리지 변경 시 React 상태 실시간 싱크
    const handleStorageChange = (
      changes: Record<string, chrome.storage.StorageChange>,
      areaName: string,
    ) => {
      if (areaName === 'local' && changes[STORAGE_KEYS.SCRAP_LIST]) {
        const next = changes[STORAGE_KEYS.SCRAP_LIST].newValue
        setScrapList(Array.isArray(next) ? (next as ScrapItem[]) : [])
      }
    }

    chrome.storage.onChanged.addListener(handleStorageChange)

    return () => {
      chrome.storage.onChanged.removeListener(handleStorageChange)
    }
  }, [])

  /**
   * 특정 스크랩 아이템 삭제 핸들러
   * React state가 아닌 storage에서 최신 목록을 읽어 갱신 — 다른 컨텍스트와의 경합 시 stale closure 방지
   */
  const deleteScrap = (id: string) => {
    if (!isExtensionContextValid() || !chrome.storage?.local) return

    chrome.storage.local.get([STORAGE_KEYS.SCRAP_LIST], (result) => {
      if (chrome.runtime.lastError) return
      const currentList = Array.isArray(result[STORAGE_KEYS.SCRAP_LIST])
        ? (result[STORAGE_KEYS.SCRAP_LIST] as ScrapItem[])
        : []
      const updatedList = currentList.filter((item) => item.id !== id)

      chrome.storage.local.set({
        [STORAGE_KEYS.SCRAP_LIST]: updatedList,
      })
    })
  }

  return {
    scrapList,
    isLoading,
    deleteScrap,
  }
}
