export const MOCK_TOP_OPINIONS = [
  "AI 에이전트 오케스트레이션",
  "생성형 AI 규제 논의",
  "디지털 웰빙 트렌드",
  "숏폼 콘텐츠 피로도",
  "데이터 주권 강화",
] as const;

/** 오버레이용 */
export const MOCK_TOP_KEYWORDS_OVERLAY = [
  "Synapse",
  "LangGraph",
  "트렌드 갭",
  "인지주권",
  "오케스트레이터",
] as const;

export const MOCK_HOT_NEWS = {
  title: "HOT NEWS",
  headline: "글로벌 AI 플랫폼, 멀티 에이전트 협업 기능 공개",
};

export const MOCK_TREND_INDEX_POINTS = [42, 55, 48, 62, 58, 71, 65, 78] as const;

export const MOCK_CARD_NEWS = [
  { id: "1", title: "AI 트렌드 2024" },
  { id: "2", title: "2024 데이터 트렌드" },
  { id: "3", title: "메타버스 트렌드" },
] as const;

export const MOCK_TOP_TRENDS = [
  "AI 에이전트",
  "데이터 레이크",
  "생성형 AI",
  "클라우드 네이티브",
  "디지털 트윈",
] as const;

export const MOCK_TOP_KEYWORDS = [
  "생성형 AI",
  "LLM",
  "빅데이터",
  "RAG",
  "멀티모달",
] as const;

export const MOCK_CHART_SERIES = [
  { label: "AI 에이전트", color: "#ef4444" },
  { label: "데이터 레이크", color: "#3b82f6" },
  { label: "플러그인 AI", color: "#22c55e" },
] as const;

export const MOCK_NEWS_FEED = [
  {
    id: "1",
    title: "삼성, AI 칩 생산 확대… HBM 수요 대응",
    date: "2024.06.12",
  },
  {
    id: "2",
    title: "구글 제미나이 시나리오 업데이트 발표",
    date: "2024.06.11",
  },
  {
    id: "3",
    title: "국내 스타트업, 에이전트 오케스트레이션 투자 유치",
    date: "2024.06.10",
  },
  {
    id: "4",
    title: "데이터 레이크 기반 트렌드 분석 도구 급부상",
    date: "2024.06.09",
  },
] as const;

export type TrendCategory = "all" | "it" | "economy" | "stock";

export const TREND_CATEGORIES: { id: TrendCategory; label: string }[] = [
  { id: "all", label: "전체" },
  { id: "it", label: "IT" },
  { id: "economy", label: "경제" },
  { id: "stock", label: "주식" },
];
