import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { FloatingWidget } from '@/features/tracking/components/FloatingWidget'
import { SYNAPSE_EXTENSION_ROOT_ID } from '@/shared/constants/extensionDom'

import widgetStyles from '@/styles/content-widget.css?inline'

const APP_ROOT_ID = 'synapse-app-within-shadow'

function mountFloatingWidget() {
  const existing = document.getElementById(SYNAPSE_EXTENSION_ROOT_ID)
  if (existing) {
    const appRoot = existing.shadowRoot?.getElementById(APP_ROOT_ID)
    if (appRoot?.childElementCount) return
    existing.remove()
  }

  const mountTarget = document.body ?? document.documentElement
  if (!mountTarget) return

  const hostContainer = document.createElement('div')
  hostContainer.id = SYNAPSE_EXTENSION_ROOT_ID
  hostContainer.style.cssText =
    'position:fixed;right:0;bottom:0;z-index:2147483647;pointer-events:auto;overflow:visible;background:transparent;border:none;'
  mountTarget.appendChild(hostContainer)

  const shadowRoot = hostContainer.attachShadow({ mode: 'open' })

  const styleEl = document.createElement('style')
  styleEl.textContent = widgetStyles
  shadowRoot.appendChild(styleEl)

  const appContainer = document.createElement('div')
  appContainer.id = APP_ROOT_ID
  appContainer.style.pointerEvents = 'auto'
  shadowRoot.appendChild(appContainer)

  createRoot(appContainer).render(
    <StrictMode>
      <FloatingWidget />
    </StrictMode>,
  )
}

/** document.body 준비 후 FAB를 마운트한다. */
export function mountFloatingWidgetWhenReady(): void {
  if (document.body) {
    mountFloatingWidget()
    return
  }

  const observer = new MutationObserver(() => {
    if (!document.body) return
    observer.disconnect()
    mountFloatingWidget()
  })
  observer.observe(document.documentElement, { childList: true })
}
