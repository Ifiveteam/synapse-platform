import { sendTrackingData } from '@/shared/api/client'
import { isBlacklisted } from '@/shared/utils/urlBlacklist'

interface ActiveSession {
  url: string
  title: string
  startTime: number
}

/**
 * 페이지 진입·이탈 이벤트를 대조해 체류 시간을 정산하는 세션 관리자.
 * 타이머 폴링 없이 startTime ↔ endTime 차이로 오차 없이 duration을 계산한다.
 */
class SessionManager {
  private currentSession: ActiveSession | null = null

  /**
   * 페이지 진입 시 새 세션을 시작한다.
   * 이전 URL과 다르면 먼저 이전 세션을 정산한 뒤 새 세션을 연다.
   */
  startSession(url: string, title: string) {
    if (isBlacklisted(url)) {
      // 민감 페이지 진입 시 기존 세션만 정산하고 새 세션은 열지 않음
      this.endCurrentSession()
      return
    }

    if (this.currentSession?.url === url) {
      // onUpdated 등으로 같은 URL이 재호출될 때 타이머 리셋 방지, 제목만 갱신
      this.currentSession.title = title
      return
    }

    if (this.currentSession) {
      this.endCurrentSession()
    }

    this.currentSession = {
      url,
      title,
      startTime: Date.now(),
    }
  }

  /**
   * 페이지 이탈·트래킹 OFF·창 포커스 상실 시 현재 세션을 정산한다.
   * 1초 미만 체류는 노이즈로 간주해 backend 전송을 생략한다.
   */
  endCurrentSession() {
    if (!this.currentSession) return

    const endTime = Date.now()
    const durationSeconds = Math.round(
      (endTime - this.currentSession.startTime) / 1000,
    )

    if (durationSeconds >= 1) {
      const payload = {
        url: this.currentSession.url,
        pageTitle: this.currentSession.title,
        durationSeconds,
        timestamp: new Date().toISOString(),
      }

      // 정산 데이터를 backend로 비동기 전송 — 실패해도 세션 메모리는 반드시 해제
      sendTrackingData(payload).catch((err) =>
        console.error('[Synapse Engine] 백엔드 전송 실패:', err),
      )
    }

    this.currentSession = null
  }
}

export const sessionManager = new SessionManager()
