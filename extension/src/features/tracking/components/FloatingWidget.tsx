/**
 * Shadow DOM 내부 FAB 및 호버 확장 메뉴.
 * 트래킹 토글·스크랩 트리거·사이드패널 열기를 호스트 페이지와 격리된 UI로 제공한다.
 */
import { useState } from 'react'
import { useTracking } from '@/features/tracking/hooks/useTracking'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

export function FloatingWidget() {
  const [isHovered, setIsHovered] = useState(false)
  const { isTracking, toggleTracking } = useTracking()

  /** 메인 버튼 클릭 → Background가 chrome.sidePanel.open() 동기 실행 (닫기는 Chrome API 미지원) */
  const handleMainButtonClick = () => {
    if (!isExtensionContextValid()) return

    chrome.runtime.sendMessage({ action: 'TOGGLE_SIDEPANEL' }).catch(() => {
      // Service Worker 비활성·컨텍스트 무효화 시 무시
    })
  }

  /** 스크랩 액션 — 다음 레이어에서 storage/API 훅과 연결 */
  const handleScrapPage = () => {
    console.log('[Synapse FAB] 현재 페이지 스크랩 트리거')
  }

  return (
    <div
      className="flex flex-col items-center gap-3 p-6 font-sans selection:bg-transparent"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 호버 시 메인 버튼 위로 서브 메뉴 확장 */}
      <div
        className={`flex flex-col gap-2 transition-all duration-300 ${
          isHovered
            ? 'pointer-events-auto translate-y-0 scale-100 opacity-100'
            : 'pointer-events-none translate-y-4 scale-95 opacity-0'
        }`}
      >
        <button
          type="button"
          onClick={handleScrapPage}
          className="flex size-10 items-center justify-center rounded-full border border-slate-100 bg-white text-slate-700 shadow-lg transition-colors hover:bg-slate-50"
          aria-label="현재 페이지 맥락 스크랩"
        >
          📌
        </button>

        <button
          type="button"
          onClick={toggleTracking}
          className={`flex size-10 items-center justify-center rounded-full border shadow-lg transition-all ${
            isTracking
              ? 'border-emerald-600 bg-emerald-500 text-white hover:bg-emerald-600'
              : 'border-rose-600 bg-rose-500 text-white hover:bg-rose-600'
          }`}
          aria-label={
            isTracking
              ? '실시간 트래킹 작동 중, 끄기'
              : '트래킹 중단됨, 켜기'
          }
          aria-pressed={isTracking}
        >
          {isTracking ? '🟢' : '🔴'}
        </button>
      </div>

      {/* Synapse 메인 FAB — 클릭 시 사이드패널 열기 */}
      <button
        type="button"
        onClick={handleMainButtonClick}
        className="flex size-14 items-center justify-center rounded-full bg-slate-900 text-xl font-bold text-white shadow-2xl transition-transform hover:scale-105 active:scale-95"
        aria-label="Synapse 사이드패널 열기"
      >
        S
      </button>
    </div>
  )
}
