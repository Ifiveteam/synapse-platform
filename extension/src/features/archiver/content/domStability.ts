/**
 * DOM 렌더링 안정화 대기.
 *
 * 역할: SPA 등 DOM mutation이 잦은 페이지에서 “멈춘 뒤” 스냅샷을 찍기 위해 기다린다.
 * 하는 일:
 * - MutationObserver로 childList/characterData/attributes 감시
 * - quietMs 동안 변경 없으면 resolve, maxWaitMs로 상한
 * - debounce 구간마다 `onStableTick` 콜백 (추가 스냅샷용)
 */
import {
  DOM_SNAPSHOT_DEBOUNCE_MS,
  DOM_STABILITY_MAX_WAIT_MS,
  DOM_STABILITY_QUIET_MS,
} from '@/features/archiver/utils/limits'

import { delay } from './domSafe'

interface StabilityOptions {
  quietMs?: number
  maxWaitMs?: number
  onStableTick?: () => void
}

export function waitForDomStability(options: StabilityOptions = {}): Promise<void> {
  const quietMs = options.quietMs ?? DOM_STABILITY_QUIET_MS
  const maxWaitMs = options.maxWaitMs ?? DOM_STABILITY_MAX_WAIT_MS
  const root = document.body

  if (!root) {
    return delay(quietMs)
  }

  return new Promise((resolve) => {
    let finished = false
    let quietTimer: number | null = null
    let debounceTimer: number | null = null

    const finish = () => {
      if (finished) return
      finished = true
      observer.disconnect()
      window.clearTimeout(maxTimer)
      if (quietTimer !== null) window.clearTimeout(quietTimer)
      if (debounceTimer !== null) window.clearTimeout(debounceTimer)
      resolve()
    }

    const scheduleQuietFinish = () => {
      if (quietTimer !== null) window.clearTimeout(quietTimer)
      quietTimer = window.setTimeout(finish, quietMs)
    }

    const onMutation = () => {
      if (debounceTimer !== null) window.clearTimeout(debounceTimer)
      debounceTimer = window.setTimeout(() => {
        try {
          options.onStableTick?.()
        } catch {
          // ignore tick failure
        }
      }, DOM_SNAPSHOT_DEBOUNCE_MS)
      scheduleQuietFinish()
    }

    let observer: MutationObserver
    try {
      observer = new MutationObserver(onMutation)
      observer.observe(root, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['class', 'style', 'hidden', 'aria-hidden'],
      })
    } catch {
      resolve()
      return
    }

    const maxTimer = window.setTimeout(finish, maxWaitMs)
    scheduleQuietFinish()
  })
}
