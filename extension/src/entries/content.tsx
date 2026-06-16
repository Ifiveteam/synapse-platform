/**
 * Synapse Content Script 진입점.
 * Shadow Root 안에 React FAB를 마운트한다.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { FloatingWidget } from '@/features/tracking/components/FloatingWidget'

import widgetStyles from '@/styles/content-widget.css?inline'

const HOST_ROOT_ID = 'synapse-extension-root'
const BOOT_KEY = '__synapseBootContentScript'

function mountSynapseWidget() {
  const existing = document.getElementById(HOST_ROOT_ID)
  if (existing) {
    const appRoot = existing.shadowRoot?.getElementById('synapse-app-within-shadow')
    // Shadow가 비어 있으면 이전 리로드/HMR 실패 잔해 — 제거 후 재마운트
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

function bootContentScript() {
  try {
    mountWhenReady()
  } catch (error) {
    console.error('[Synapse] FAB 마운트 실패:', error)
  }
}

// Rolldown이 export를 제거해도 Vite 플러그인·CRXJS 로더가 globalThis로 재호출 가능
;(globalThis as Record<string, unknown>)[BOOT_KEY] = bootContentScript

/** CRXJS 로더 진입점 */
export function onExecute() {
  bootContentScript()
}

bootContentScript()
