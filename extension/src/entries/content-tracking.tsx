/**
 * Tracking content script 진입점 (top frame only).
 *
 * 역할: FAB·auth bridge만 주입한다. Archiver 추출은 `content-archiver.ts`가 담당.
 */
import { bootTrackingContentScript } from '@/features/tracking/content/bootTrackingContent'

const BOOT_KEY = '__synapseBootTrackingContent'

function bootTrackingContentEntry(): void {
  try {
    bootTrackingContentScript()
  } catch (error) {
    console.error('[Synapse] tracking content script boot 실패:', error)
  }
}

;(globalThis as Record<string, unknown>)[BOOT_KEY] = bootTrackingContentEntry

/** CRXJS 로더 진입점 */
export function onExecute() {
  bootTrackingContentEntry()
}

bootTrackingContentEntry()
