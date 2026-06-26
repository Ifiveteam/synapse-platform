/**
 * Background Service Worker용 트래킹 수집 엔진.
 * chrome.storage 토글 상태를 감시하며, ON일 때만 탭·창 센서를 동적으로 장착한다.
 *
 * 데이터 흐름: storage 토글 → 탭/창 이벤트 → sessionManager → backend API
 */
import { STORAGE_KEYS } from '@/shared/constants/storageKeys'
import { sessionManager } from './sessionManager'

let isEngineRunning = false

/** 같은 창 내 탭 전환 — 활성 탭 URL·제목으로 세션 교체 */
function handleTabActivated(activeInfo: chrome.tabs.OnActivatedInfo) {
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    // 닫힌 탭 조회 등 tabs.get 실패 시 무시
    if (chrome.runtime.lastError || !tab?.url) return
    sessionManager.startSession(tab.url, tab.title || '')
  })
}

/** 탭 로딩 완료·SPA URL 변경 — 현재 포커스 탭만 추적 */
function handleTabUpdated(
  _tabId: number,
  changeInfo: chrome.tabs.OnUpdatedInfo,
  tab: chrome.tabs.Tab,
) {
  // 백그라운드 탭 로딩 이벤트는 수집 대상이 아님
  if (!tab.active || !tab.url) return

  const shouldTrack =
    changeInfo.status === 'complete' || changeInfo.url !== undefined

  if (shouldTrack) {
    sessionManager.startSession(tab.url, tab.title || '')
  }
}

/**
 * 멀티 모니터·다중 창 포커스 전환 감지.
 * onActivated만으로는 창 간 이동 시 이전 창 세션이 정산되지 않는 문제를 보완한다.
 */
function handleWindowFocusChanged(windowId: number) {
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    // 크롬 밖(다른 앱)으로 포커스 이탈 — 체류 시간 정산 종료
    sessionManager.endCurrentSession()
    return
  }

  chrome.tabs.query({ active: true, windowId }, (tabs) => {
    const activeTab = tabs[0]
    if (activeTab?.url) {
      sessionManager.startSession(activeTab.url, activeTab.title || '')
    } else {
      // 포커스된 창에 유효 URL 탭이 없으면 이전 세션 누적 방지
      sessionManager.endCurrentSession()
    }
  })
}

/**
 * 유저 토글 상태에 따라 탭·창 센서를 동적으로 탈부착한다.
 * OFF 시 리스너를 모두 해제해 유저가 거부한 동안 리소스·네트워크 사용을 차단한다.
 */
export function updateEngineState(isTrackingEnabled: boolean) {
  if (!isTrackingEnabled) {
    console.log('[Synapse Engine] 트래킹 수집 완전히 중단')

    chrome.tabs.onActivated.removeListener(handleTabActivated)
    chrome.tabs.onUpdated.removeListener(handleTabUpdated)
    chrome.windows.onFocusChanged.removeListener(handleWindowFocusChanged)
    sessionManager.endCurrentSession()
    isEngineRunning = false
    return
  }

  // storage onChanged·초기화가 연속 호출돼도 리스너 중복 등록 방지
  if (isEngineRunning) return

  console.log('[Synapse Engine] 트래킹 수집 가동 시작')
  isEngineRunning = true

  chrome.tabs.onActivated.addListener(handleTabActivated)
  chrome.tabs.onUpdated.addListener(handleTabUpdated)
  chrome.windows.onFocusChanged.addListener(handleWindowFocusChanged)

  // 가동 직후 현재 활성 탭을 첫 세션으로 즉시 등록
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0]
    if (currentTab?.url) {
      sessionManager.startSession(currentTab.url, currentTab.title || '')
    }
  })
}

/**
 * Service Worker 기동 시 엔진을 초기화하고 storage 토글 변경을 구독한다.
 * FAB·사이드패널 스위치 조작이 Background 수집 ON/OFF로 즉시 반영된다.
 */
export function initializeTrackingEngine() {
  chrome.storage.local.get([STORAGE_KEYS.TRACKING_STATUS], (result) => {
    updateEngineState(Boolean(result[STORAGE_KEYS.TRACKING_STATUS]))
  })

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'local' && changes[STORAGE_KEYS.TRACKING_STATUS]) {
      updateEngineState(
        Boolean(changes[STORAGE_KEYS.TRACKING_STATUS].newValue),
      )
    }
  })
}
