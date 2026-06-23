export type ScrapViewMode = "list" | "graph";
export type ScrapFilterMode = "all" | "category" | "date";

export interface ScrapGraphNode {
  id: string;
  label: string;
  cx: number;
  cy: number;
  r: number;
  fill: string;
  isCenter?: boolean;
  summary?: string;
  /** 스크랩 메인에서 노드 클릭 시 상세로 이동할 때 사용 */
  scrapId?: string;
}

export const SCRAP_GRAPH_EDGES: [string, string][] = [
  ["me", "n1"],
  ["me", "n2"],
  ["me", "n3"],
  ["me", "n4"],
  ["n1", "n2"],
  ["n2", "n5"],
  ["n3", "n4"],
  ["n4", "n6"],
  ["n1", "n5"],
];

export const SCRAP_GRAPH_NODES: ScrapGraphNode[] = [
  {
    id: "me",
    label: "나",
    cx: 400,
    cy: 240,
    r: 36,
    fill: "#f472b6",
    isCenter: true,
    summary: "내 스크랩 키워드 허브",
  },
  {
    id: "n1",
    label: "AI 에이전트",
    cx: 280,
    cy: 140,
    r: 28,
    fill: "#60a5fa",
    summary: "멀티 에이전트 오케스트레이션 관련 스크랩",
    scrapId: "1",
  },
  {
    id: "n2",
    label: "데이터 시각화",
    cx: 520,
    cy: 120,
    r: 24,
    fill: "#a78bfa",
    summary: "그래프·레이더 차트 레퍼런스",
  },
  {
    id: "n3",
    label: "트렌드 분석",
    cx: 220,
    cy: 300,
    r: 26,
    fill: "#34d399",
    summary: "Aggregator 트렌드 갭 노트",
    scrapId: "2",
  },
  {
    id: "n4",
    label: "인지주권",
    cx: 560,
    cy: 280,
    r: 22,
    fill: "#fbbf24",
    summary: "필터버블·이상향 관련 글",
    scrapId: "4",
  },
  {
    id: "n5",
    label: "LangGraph",
    cx: 480,
    cy: 200,
    r: 20,
    fill: "#22d3ee",
    summary: "LangGraph 파이프라인 문서",
    scrapId: "3",
  },
  {
    id: "n6",
    label: "UX 리서치",
    cx: 620,
    cy: 360,
    r: 18,
    fill: "#fb7185",
    summary: "사이드바·오버레이 와이어프레임",
  },
];

export const SCRAP_LIST_ITEMS = [
  {
    id: "1",
    title: "AI 에이전트 트렌드 2024",
    category: "기술",
    savedAt: "2025.06.11",
  },
  {
    id: "2",
    title: "트렌드 갭 분석 노트",
    category: "트렌드",
    savedAt: "2025.06.08",
  },
  {
    id: "3",
    title: "프로파일 그래프 해석",
    category: "Profiler",
    savedAt: "2025.06.05",
  },
  {
    id: "4",
    title: "이상향 설계 프레임워크",
    category: "Navigator",
    savedAt: "2025.06.01",
  },
] as const;

export interface ScrapDetail {
  id: string;
  title: string;
  url: string;
  savedAt: string;
  source: string;
  category: string;
  tags: string[];
  previewLabel: string;
  content: string;
  summary: string;
  relatedAnalyses: { id: string; title: string; checked: boolean }[];
}

const BASE_SCRAP_DETAIL: Omit<
  ScrapDetail,
  "id" | "title" | "url" | "savedAt" | "source" | "category" | "tags" | "previewLabel"
> = {
  content:
    "2024년 AI 에이전트 시장은 단일 모델 중심에서 멀티 에이전트 오케스트레이션으로 빠르게 이동하고 있습니다. " +
    "기업들은 에이전트 간 역할 분담, 메모리 공유, 휴먼 인 더 루프 검증을 표준 아키텍처로 채택하는 추세입니다. " +
    "특히 트렌드 수집·요약·개인화 추천 파이프라인에서 Aggregator형 에이전트와 Profiler형 사용자 모델의 결합이 두드러집니다. " +
    "동시에 인지주권과 필터버블 완화를 위한 Navigator형 이상향 설계가 UX 차별화 요소로 부상하고 있습니다.",
  summary:
    "핵심 요약: 멀티 에이전트 오케스트레이션이 2024 트렌드의 중심이며, Aggregator·Profiler·Navigator 조합이 개인화 플랫폼의 표준 패턴으로 자리 잡고 있습니다.",
  relatedAnalyses: [
    { id: "5", title: "개인성향 분석 #5", checked: true },
    { id: "4", title: "개인성향 분석 #4", checked: true },
    { id: "2", title: "개인성향 분석 #2", checked: false },
  ],
};

export const MOCK_SCRAP_DETAILS: Record<string, ScrapDetail> = {
  "1": {
    ...BASE_SCRAP_DETAIL,
    id: "1",
    title: "AI 에이전트 트렌드 2024",
    url: "https://example.com/articles/ai-agent-trends-2024",
    savedAt: "2025.06.11",
    source: "Tech Insights Weekly",
    category: "기술",
    tags: ["AI", "트렌드", "2024", "에이전트"],
    previewLabel: "웹사이트 미리보기",
  },
  "2": {
    ...BASE_SCRAP_DETAIL,
    id: "2",
    title: "트렌드 갭 분석 노트",
    url: "https://example.com/notes/trend-gap-analysis",
    savedAt: "2025.06.08",
    source: "내부 리서치 노트",
    category: "트렌드",
    tags: ["트렌드", "갭분석", "Aggregator"],
    previewLabel: "노트 미리보기",
    content:
      "현재 수집된 트렌드 키워드와 사용자 관심사 사이의 갭을 정리한 메모입니다. " +
      "상위 5개 트렌드 중 2개는 이미 스크랩·분석과 연결되어 있고, 나머지는 신규 탐색 후보로 분류했습니다.",
    summary:
      "핵심 요약: 트렌드 키워드 5개 중 3개가 개인 분석·스크랩과 겹치며, '멀티 에이전트 UX'와 '인지주권'이 신규 탐색 우선순위입니다.",
  },
  "3": {
    ...BASE_SCRAP_DETAIL,
    id: "3",
    title: "프로파일 그래프 해석",
    url: "https://example.com/docs/profiler-graph-guide",
    savedAt: "2025.06.05",
    source: "Profiler Docs",
    category: "Profiler",
    tags: ["Profiler", "그래프", "성향분석"],
    previewLabel: "문서 미리보기",
    content:
      "Profiler 그래프의 노드·엣지는 사용자의 관심 키워드와 행동 신호를 가중치로 연결합니다. " +
      "중심 노드는 현재 가장 강한 정체성 축을 나타내며, 주변 클러스터는 확장 가능한 관심 영역을 시사합니다.",
    summary:
      "핵심 요약: 중심 노드 = 핵심 정체성, 주변 클러스터 = 성장 가능 관심사. 그래프 밀도가 높을수록 탐구형 성향이 강합니다.",
    relatedAnalyses: [
      { id: "5", title: "개인성향 분석 #5", checked: true },
      { id: "1", title: "개인성향 분석 #1", checked: false },
    ],
  },
  "4": {
    ...BASE_SCRAP_DETAIL,
    id: "4",
    title: "이상향 설계 프레임워크",
    url: "https://example.com/framework/ideal-design",
    savedAt: "2025.06.01",
    source: "Navigator Playbook",
    category: "Navigator",
    tags: ["Navigator", "이상향", "UX"],
    previewLabel: "프레임워크 미리보기",
    content:
      "이상향은 단순 목표 문장이 아니라, 가치·행동·피드백 루프가 연결된 설계 단위입니다. " +
      "확장형·균형형·탐구형 등 유형별로 퀘스트 템플릿과 콘텐츠 필터가 달라져야 합니다.",
    summary:
      "핵심 요약: 이상향 = 가치 + 행동 + 피드백 루프. 유형별 퀘스트·필터를 분기하는 것이 Navigator 설계의 핵심입니다.",
    relatedAnalyses: [
      { id: "4", title: "개인성향 분석 #4", checked: true },
    ],
  },
};

export function getScrapDetail(id: string): ScrapDetail | undefined {
  return MOCK_SCRAP_DETAILS[id];
}
