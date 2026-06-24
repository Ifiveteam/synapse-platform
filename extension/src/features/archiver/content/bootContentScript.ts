/**
 * Content script Archiver 진입 레이어.
 * `entries/content.tsx`는 FAB(트래킹)와 이 부트스트랩만 호출한다.
 */
import { initPageContextBridge } from '@/features/archiver/content/initPageContextBridge'

export function bootArchiverContentScript(): void {
  initPageContextBridge()
}
