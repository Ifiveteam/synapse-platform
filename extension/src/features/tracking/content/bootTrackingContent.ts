/**
 * Tracking content script 부트스트랩.
 *
 * 역할: top-frame 전용 content script (`entries/content-tracking.tsx`) 진입 레이어.
 * 하는 일: 웹↔익스텐션 auth bridge + FAB Shadow DOM 마운트.
 */
import { initAuthBridge } from '@/shared/auth/authBridge'

import { mountFloatingWidgetWhenReady } from './mountFloatingWidget'

export function bootTrackingContentScript(): void {
  initAuthBridge()
  mountFloatingWidgetWhenReady()
}
