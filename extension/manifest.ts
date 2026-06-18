import { defineManifest } from '@crxjs/vite-plugin'

export default defineManifest({
  manifest_version: 3,
  name: 'AI Chat & Scraper Extension',
  version: '1.0.0',
  description:
    '페이지 컨텍스트 기반 실시간 트래킹, AI 채팅 및 스크랩 보관함 보조 도구',

  // 기획 기능 구현을 위한 브라우저 핵심 권한 정의
  permissions: [
    'sidePanel', // 메인 FAB 클릭 시 브라우저 우측 사이드패널 창 토글용
    'activeTab', // 유저가 현재 보고 있는 탭의 본문 텍스트 파싱용
    'storage', // FAB와 사이드패널 헤더 간 트래킹 토글 스위치 상태 실시간 동기화용
    'tabs', // 유저 제어형 실시간 URL 및 체류 시간 추적 모니터링용
    'windows', // 멀티 모니터·다중 창 포커스 전환 시 세션 정산용
  ],

  // 실시간 행동 데이터 수집 및 본문 스크랩 + Vite dev 서버(HMR) 접근
  host_permissions: ['<all_urls>', 'http://localhost:5173/*'],

  // 유저 제어형 실시간 행동 데이터 수집 환경 (Service Worker)
  background: {
    service_worker: 'src/entries/background.ts',
    type: 'module',
  },

  // 플로팅 액션 버튼 (FAB) 및 확장 메뉴 주입 (Content Script 환경)
  content_scripts: [
    {
      matches: ['<all_urls>'],
      js: ['src/entries/content.tsx'],
      // Tailwind CSS나 Shadcn UI 스타일링이 웹페이지에 깨짐 없이 주입되도록 보장
      run_at: 'document_idle',
    },
  ],

  // 컨텍스트 AI 채팅 및 스크랩 보관함 환경 (Sidepanel 환경)
  side_panel: {
    default_path: 'src/sidepanel/index.html',
  },

  // setPanelBehavior(openPanelOnActionClick) 및 툴바 아이콘용
  action: {
    default_title: 'Synapse',
  },
})
