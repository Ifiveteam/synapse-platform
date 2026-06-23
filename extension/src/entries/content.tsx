/**
 * Synapse Content Script 진입점.
 * - Tracking: Shadow Root FAB 마운트
 * - Archiver: 페이지 본문 추출 브릿지 (content ↔ sidepanel)
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { bootArchiverContentScript } from '@/features/archiver/content/bootContentScript'
import { FloatingWidget } from '@/features/tracking/components/FloatingWidget'
import { initAuthBridge } from '@/shared/auth/authBridge'

import widgetStyles from '@/styles/content-widget.css?inline'

const HOST_ROOT_ID = 'synapse-extension-root'
const BOOT_KEY = '__synapseBootContentScript'

function mountSynapseWidget() {
  const existing = document.getElementById(HOST_ROOT_ID)
  if (existing) {
    const appRoot = existing.shadowRoot?.getElementById('synapse-app-within-shadow')
    if (appRoot?.childElementCount) return
    existing.remove()
  }

  const mountTarget = document.body ?? document.documentElement
  if (!mountTarget) return

  const hostContainer = document.createElement('div')
  hostContainer.id = HOST_ROOT_ID
  hostContainer.style.cssText =
    'position:fixed;right:0;bottom:0;z-index:2147483647;pointer-events:auto;overflow:visible;background:transparent;border:none;'
  mountTarget.appendChild(hostContainer)

  const shadowRoot = hostContainer.attachShadow({ mode: 'open' })

  const styleEl = document.createElement('style')
  styleEl.textContent = widgetStyles
  shadowRoot.appendChild(styleEl)

  const appContainer = document.createElement('div')
  appContainer.id = 'synapse-app-within-shadow'
  appContainer.style.pointerEvents = 'auto'
  shadowRoot.appendChild(appContainer)

  createRoot(appContainer).render(
    <StrictMode>
      <FloatingWidget />
    </StrictMode>,
  )
}

function mountWhenReady() {
  if (document.body) {
    mountSynapseWidget()
    return
  }

  const observer = new MutationObserver(() => {
    if (!document.body) return
    observer.disconnect()
    mountSynapseWidget()
  })
  observer.observe(document.documentElement, { childList: true })
}

function bootArchiverBridge() {
  bootArchiverContentScript()
}

function bootTrackingFab() {
  initAuthBridge()
  mountWhenReady()
}

function bootContentScript() {
  try {
    const topFrame = window === window.top

    bootArchiverBridge()

    if (topFrame) {
      bootTrackingFab()
    }
  } catch (error) {
    console.error('[Synapse] content script boot 실패:', error)
  }
}

;(globalThis as Record<string, unknown>)[BOOT_KEY] = bootContentScript

/** CRXJS 로더 진입점 */
export function onExecute() {
  bootContentScript()
}

bootContentScript()
