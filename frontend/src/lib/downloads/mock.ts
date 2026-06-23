export const CHROME_EXTENSION = {
  name: "Synapse Scraper",
  version: "0.3.1",
  description:
    "브라우저에서 바로 스크랩하고 Synapse 플랫폼과 연동합니다. " +
    "웹 페이지를 저장하고 키워드 그래프에 반영할 수 있습니다.",
  chromeMinVersion: "120",
  storeUrl: "https://chrome.google.com/webstore", // mock — 실제 스토어 URL로 교체
  fileName: "synapse-scraper-v0.3.1.zip",
  updatedAt: "2025.06.10",
} as const;

export const INSTALL_STEPS = [
  "아래 버튼으로 확장 프로그램 파일을 받습니다.",
  "Chrome 주소창에 chrome://extensions 를 입력합니다.",
  "우측 상단에서 개발자 모드를 켭니다.",
  "「압축해제된 확장 프로그램을 로드합니다」를 누르고 받은 폴더를 선택합니다.",
] as const;
