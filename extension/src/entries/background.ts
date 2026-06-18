/**
 * Manifest V3 Background Service Worker 진입점.
 * 사이드패널 기본 동작 설정과 트래킹 엔진 초기화를 담당한다.
 */
import { initializeTrackingEngine } from '@/features/tracking/services/trackingEngine'

/** manifest side_panel.default_path 와 동일해야 함 */
const SIDE_PANEL_PATH = 'src/sidepanel/index.html'

async function enableSidePanelForTab(tabId: number) {
  await chrome.sidePanel.setOptions({
    tabId,
    path: SIDE_PANEL_PATH,
    enabled: true,
  })
}

/** SW 재시작·설치 후에도 이미 열린 탭에 sidePanel 옵션 적용 */
async function enableSidePanelForAllTabs() {
  await chrome.sidePanel.setOptions({
    path: SIDE_PANEL_PATH,
    enabled: true,
  })

  const tabs = await chrome.tabs.query({})
  await Promise.all(
    tabs.map((tab) => {
      if (tab.id == null) return Promise.resolve()
      return enableSidePanelForTab(tab.id).catch(() => {
        // chrome:// 등 시스템 탭은 setOptions 실패 — 무시
      })
    }),
  )
}

void chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error('[background] sidePanel setup failed:', error))

chrome.runtime.onInstalled.addListener(() => {
  void enableSidePanelForAllTabs()
})

chrome.runtime.onStartup.addListener(() => {
  void enableSidePanelForAllTabs()
})

// 새 탭·네비게이션 완료 시에도 per-tab 옵션 보장
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status !== 'complete') return

  void enableSidePanelForTab(tabId).catch(() => {
    // chrome:// 등 시스템 페이지는 setOptions 실패 — 무시
  })
})

// storage 토글 감시 시작 — 유저가 ON할 때만 탭·창 센서 가동
initializeTrackingEngine()

/**
 * Content Script FAB → 사이드패널 열기.
 * open() 전에 반드시 setOptions(path, enabled)가 해당 tabId에 적용되어야 함.
 */
chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.action !== 'TOGGLE_SIDEPANEL') return

  const tabId = sender.tab?.id
  const windowId = sender.tab?.windowId
  if (tabId == null || windowId == null) {
    console.warn('[background] TOGGLE_SIDEPANEL: tab/window 없음', sender)
    return
  }

  void (async () => {
    try {
      await enableSidePanelForTab(tabId)
      await chrome.sidePanel.open({ tabId, windowId })
    } catch (error) {
      console.error('[background] sidePanel.open 실패:', error)
    }
  })()
})
