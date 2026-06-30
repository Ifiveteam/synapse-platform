export interface SidebarScrap {
  id: string;
  sessionId: string;
  title: string;
  savedAt: string;
}

export interface SidebarChat {
  id: string;
  title: string;
  updatedAt: string;
}

/** 현재 적용 중인 이상향 표시 라벨 (초기값 — 백엔드 로드 전) */
export const MOCK_ACTIVE_IDEAL_LABEL: string | null = null;

export const MOCK_CHATS: SidebarChat[] = [
  { id: "c1", title: "이번 주 성장 방향 논의", updatedAt: "오늘" },
  { id: "c2", title: "확장형 이상향 피드백", updatedAt: "어제" },
  { id: "c3", title: "스크랩 요약 요청", updatedAt: "3일 전" },
  { id: "c4", title: "Navigator 퀘스트 점검", updatedAt: "1주 전" },
];
