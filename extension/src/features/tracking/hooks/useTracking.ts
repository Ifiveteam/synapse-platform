import { useEffect, useState } from 'react'
import { STORAGE_KEYS } from '@/shared/constants/storageKeys'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

/**
 * FAB(Content Script)와 사이드패널이 공유하는 트래킹 스위치 상태 훅.
 * chrome.storage.local을 단일 진실 소스로 두어 양쪽 UI가 실시간 동기화되게 한다.
 */
export function useTracking() {
  const [isTracking, setIsTracking] = useState(false)

  useEffect(() => {
    if (!isExtensionContextValid() || !chrome.storage?.local) {
      return
    }

    // 마운트 시 storage에 저장된 토글 상태를 읽어 UI 초기값 동기화
    chrome.storage.local.get([STORAGE_KEYS.TRACKING_STATUS], (result) => {
      if (chrome.runtime.lastError) return
      if (result[STORAGE_KEYS.TRACKING_STATUS] !== undefined) {
        setIsTracking(Boolean(result[STORAGE_KEYS.TRACKING_STATUS]))
      }
    })

    // 다른 컨텍스트(FAB ↔ 사이드패널 ↔ Background)에서 토글이 바뀌면 React 상태 갱신
    const handleStorageChange = (
      changes: Record<string, chrome.storage.StorageChange>,
      areaName: string,
    ) => {
      if (areaName === 'local' && changes[STORAGE_KEYS.TRACKING_STATUS]) {
        setIsTracking(Boolean(changes[STORAGE_KEYS.TRACKING_STATUS].newValue))
      }
    }

    chrome.storage.onChanged.addListener(handleStorageChange)

    return () => {
      chrome.storage.onChanged.removeListener(handleStorageChange)
    }
  }, [])

  /**
   * 로컬 state를 직접 바꾸지 않고 storage만 갱신한다.
   * onChanged 리스너가 모든 컨텍스트의 UI를 한 번에 동기화한다.
   */
  const setTracking = (enabled: boolean) => {
    if (!isExtensionContextValid() || !chrome.storage?.local) {
      return
    }

    chrome.storage.local.set({
      [STORAGE_KEYS.TRACKING_STATUS]: enabled,
    })
  }

  /** FAB 등 클릭 토글 UI용 — storage 단일 소스 유지 */
  const toggleTracking = () => {
    setTracking(!isTracking)
  }

  return {
    isTracking,
    setTracking,
    toggleTracking,
  }
}
