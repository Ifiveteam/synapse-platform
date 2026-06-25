/**
 * 페이지 본문 추출 오케스트레이션 (async public API).
 *
 * 역할: 안정화 대기 + 다중 스냅샷 + 채점을 묶어 최종 TabContext body 문자열을 반환한다.
 * 하는 일:
 * 1. 즉시 스냅샷 (`strategies.extractPageTextSnapshot`)
 * 2. `domStability` 대기 — mutation마다 재스냅샷
 * 3. 종료 후 delay + 추가 스냅샷
 * 4. `scoring.considerSnapshot` tracker 중 최고 품질 반환 (없으면 final fallback)
 *
 * Shadow DOM은 clone 없이 순회만 하며, 전 구간 `domSafe.runSafe`로 fault-tolerant하다.
 */
import { DOM_SNAPSHOT_DELAY_MS } from '@/features/archiver/utils/limits'

import { delay, runSafe } from './domSafe'
import { waitForDomStability } from './domStability'
import { considerSnapshot } from './scoring'
import { extractPageTextSnapshot } from './strategies'
import type { ExtractPageTextOptions } from './types'
import { truncatePageText } from './textNormalize'

export async function extractVisiblePageText(
  options: ExtractPageTextOptions = {},
): Promise<string> {
  const tracker = { best: '', bestScore: 0 }

  const snapshot = () => {
    considerSnapshot(
      runSafe('snapshot', () => extractPageTextSnapshot(options), ''),
      tracker,
    )
  }

  snapshot()

  try {
    await waitForDomStability({ onStableTick: snapshot })
  } catch {
    // proceed with best effort
  }

  snapshot()
  await delay(DOM_SNAPSHOT_DELAY_MS)
  snapshot()

  if (tracker.best) {
    return truncatePageText(tracker.best)
  }

  return runSafe('final-snapshot', () => extractPageTextSnapshot(options), '')
}
