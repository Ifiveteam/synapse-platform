// 사이드바 표시용 경량 타입 (스크랩·채팅 목록).

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
