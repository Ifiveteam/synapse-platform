import type { IdealType } from "@/lib/navigator/types";

export interface SidebarScrap {
  id: string;
  title: string;
  savedAt: string;
}

export interface SidebarChat {
  id: string;
  title: string;
  updatedAt: string;
}

export const MOCK_ACTIVE_IDEAL: IdealType = "expansion";

export const MOCK_SCRAPS: SidebarScrap[] = [
  { id: "1", title: "AI 에이전트 트렌드 2024", savedAt: "2시간 전" },
  { id: "2", title: "트렌드 갭 분석 노트", savedAt: "어제" },
  { id: "3", title: "프로파일 그래프 해석", savedAt: "3일 전" },
];

export const MOCK_CHATS: SidebarChat[] = [
  { id: "c1", title: "이번 주 성장 방향 논의", updatedAt: "오늘" },
  { id: "c2", title: "확장형 이상향 피드백", updatedAt: "어제" },
  { id: "c3", title: "스크랩 요약 요청", updatedAt: "3일 전" },
  { id: "c4", title: "Navigator 퀘스트 점검", updatedAt: "1주 전" },
];
