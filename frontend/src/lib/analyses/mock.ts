export type AnalysisStatus = "completed" | "pending";

export interface AnalysisResultItem {
  id: string;
  title: string;
  date: string;
  status: AnalysisStatus;
}

export interface AnalysisDetail {
  id: string;
  title: string;
  date: string;
  status: AnalysisStatus;
  characterName: string;
  typeName: string;
  description: string;
  tags: string[];
  keywords: string[];
  similarCharacter: {
    name: string;
    imageLabel: string;
  };
}

export const MOCK_ANALYSIS_RESULTS: AnalysisResultItem[] = [
  { id: "5", title: "개인성향 분석 #5", date: "2025.06.11", status: "completed" },
  { id: "4", title: "개인성향 분석 #4", date: "2025.06.04", status: "completed" },
  { id: "3", title: "개인성향 분석 #3", date: "2025.05.28", status: "pending" },
  { id: "2", title: "개인성향 분석 #2", date: "2025.05.21", status: "completed" },
  { id: "1", title: "개인성향 분석 #1", date: "2025.05.14", status: "pending" },
];

const BASE_DETAIL: Omit<AnalysisDetail, "id" | "title" | "date" | "status"> = {
  characterName: "탐구형 탐험가",
  typeName: "탐구형 유형",
  description:
    "새로운 정보와 아이디어에 열린 태도를 가지며, 스스로 목표를 세우고 꾸준히 실행하는 성향입니다. " +
    "타인의 의견을 존중하면서도 자신만의 관점으로 세상을 해석합니다. " +
    "데이터와 경험을 연결해 패턴을 찾는 데 강점이 있으며, 협업 상황에서도 자연스럽게 방향을 제시합니다.",
  tags: ["자신감", "노력파", "아이디어 뱅크", "리더십 강함", "친화력 좋음"],
  keywords: [
    "낙천적인 성격",
    "새로운 도전에 대한 두려움 없음",
    "타인의 의견을 존중함",
    "끈기 있게 일을 완수함",
    "솔직한 감정 표현",
  ],
  similarCharacter: {
    name: "캐릭터 이름",
    imageLabel: "캐릭터 이미지",
  },
};

export const MOCK_ANALYSIS_DETAILS: Record<string, AnalysisDetail> =
  Object.fromEntries(
    MOCK_ANALYSIS_RESULTS.map((item) => [
      item.id,
      {
        ...BASE_DETAIL,
        id: item.id,
        title: item.title,
        date: item.date,
        status: item.status,
        typeName:
          item.id === "5"
            ? "탐구형 유형"
            : item.id === "4"
              ? "확장형 유형"
              : item.id === "2"
                ? "균형형 유형"
                : BASE_DETAIL.typeName,
      },
    ]),
  );

export function getAnalysisDetail(id: string): AnalysisDetail | undefined {
  return MOCK_ANALYSIS_DETAILS[id];
}

export const ANALYSIS_PAGE_SIZE = 5;
