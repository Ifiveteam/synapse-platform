export interface IdealAxis {
  /** 축 한글 라벨 (Synapse 8축) */
  label: string;
  /** 현재 점수 0~100 */
  current: number;
  /** 이상향 목표 점수 0~100 */
  ideal: number;
}

export interface IdealGuideStep {
  title: string;
  detail: string;
}

export interface IdealProfile {
  id: string;
  name: string;
  subtitle: string;
  createdAt: string;
  tags: string[];
  isActive?: boolean;
  /** 한 줄 요약 */
  summary?: string;
  /** 현재 vs 이상향 8축 비교 */
  axes: IdealAxis[];
  /** 이상향을 위한 행동 가이드 */
  guide: IdealGuideStep[];
}

const AXIS_LABELS = [
  "탐색",
  "분석",
  "창의",
  "실행",
  "성취동기",
  "자율",
  "사회성",
  "감수성",
];

function axes(current: number[], ideal: number[]): IdealAxis[] {
  return AXIS_LABELS.map((label, i) => ({
    label,
    current: current[i],
    ideal: ideal[i],
  }));
}

export const MOCK_IDEAL_PROFILES: IdealProfile[] = [
  {
    id: "a",
    name: "이상향 A",
    subtitle: "기술·경제 탐구형",
    createdAt: "2024.03.01",
    tags: ["정보탐색", "지식습득", "기타"],
    isActive: true,
    summary: "넓은 탐색 위에 분석력과 실행력을 더해 깊이 있는 탐구형으로.",
    axes: axes(
      [70, 40, 55, 45, 50, 65, 40, 50],
      [85, 75, 55, 60, 60, 70, 45, 50],
    ),
    guide: [
      {
        title: "특정 주제 심층 분석 콘텐츠 시청",
        detail: "관심 분야 하나를 골라 개요 영상 대신 심층 분석 영상을 본다.",
      },
      {
        title: "본 내용을 직접 정리·실습",
        detail: "시청 후 핵심을 노트로 정리하거나 간단히 따라 해 본다.",
      },
      {
        title: "전문가 채널 1개 구독",
        detail: "신뢰할 만한 전문가 채널을 구독해 흐름을 꾸준히 따라간다.",
      },
    ],
  },
  {
    id: "b",
    name: "이상향 B",
    subtitle: "감성 콘텐츠 중심",
    createdAt: "2024.02.15",
    tags: ["정서·위로", "창의·표현", "기타"],
    summary: "창의·표현과 감수성을 키워 정서적으로 풍부한 소비로.",
    axes: axes(
      [50, 45, 55, 40, 45, 50, 55, 60],
      [55, 45, 80, 45, 50, 55, 65, 85],
    ),
    guide: [
      {
        title: "창작 과정 콘텐츠 시청",
        detail: "완성물보다 만드는 과정을 보여주는 영상을 찾아본다.",
      },
      {
        title: "다양한 감정 스펙트럼의 작품 접하기",
        detail: "익숙한 톤 밖의 예술·이야기 콘텐츠를 의도적으로 본다.",
      },
      {
        title: "감상을 표현으로 남기기",
        detail: "본 작품에 대한 짧은 감상을 글·그림 등으로 남긴다.",
      },
    ],
  },
  {
    id: "c",
    name: "이상향 C",
    subtitle: "균형 잡힌 생활",
    createdAt: "2024.01.28",
    tags: ["자기계발", "실용 지향", "기타"],
    summary: "강점은 유지하면서 약한 축을 고르게 보완해 균형으로.",
    axes: axes(
      [60, 55, 50, 45, 50, 60, 45, 55],
      [65, 65, 60, 65, 60, 65, 65, 65],
    ),
    guide: [
      {
        title: "실행형 튜토리얼 따라 하기",
        detail: "보고 끝내지 말고 한 가지를 직접 실행해 본다.",
      },
      {
        title: "공동체 기반 콘텐츠 참여",
        detail: "댓글·커뮤니티에서 의견을 나누며 사회성을 키운다.",
      },
      {
        title: "주간 회고 루틴",
        detail: "한 주 소비를 돌아보고 다음 주 목표를 가볍게 정한다.",
      },
    ],
  },
];

export function getIdealById(id: string): IdealProfile | undefined {
  return MOCK_IDEAL_PROFILES.find((item) => item.id === id);
}

// ── 이상향 설정 흐름 (분석 선택 → 3안 추천) mock ──────────────

export const SETUP_AXIS_LABELS = [
  "탐색",
  "분석",
  "창의",
  "실행",
  "성취동기",
  "자율",
  "사회성",
  "감수성",
];

/** 선택한 분석의 현재 8축 (mock) */
export const MOCK_SETUP_CURRENT = [70, 45, 55, 45, 50, 65, 40, 55];

export type ProposalType = "OPPOSITE" | "DEEPEN" | "BALANCE";

export interface IdealProposal {
  type: ProposalType;
  label: string;
  summary: string;
  /** 펼쳤을 때 보일 자세한 설명 */
  detail: string;
  /** 목표 8축 */
  ideal: number[];
}

export const MOCK_SETUP_PROPOSALS: IdealProposal[] = [
  {
    type: "OPPOSITE",
    label: "반대형",
    summary:
      "두드러진 축은 낮추고 약한 축을 끌어올려 필터버블에서 벗어나는 방향.",
    detail:
      "지금 강하게 굳어 있는 탐색·자율 성향을 의도적으로 낮추고, 상대적으로 약한 분석·실행·사회성을 끌어올립니다. " +
      "익숙한 소비 패턴에서 벗어나 새로운 시각과 균형 잡힌 정보 습관을 만들고 싶을 때 적합합니다.",
    ideal: [55, 70, 55, 60, 55, 55, 60, 55],
  },
  {
    type: "DEEPEN",
    label: "강점심화형",
    summary: "지금의 강점(탐색·창의·자율)을 더 밀어 전문화하는 방향.",
    detail:
      "이미 잘하고 있는 탐색·창의·자율 축을 한층 더 끌어올려 한 분야의 전문성을 깊게 다집니다. " +
      "강점을 정체성으로 굳히고 깊이 있는 몰입을 원할 때 적합하며, 약한 축은 크게 건드리지 않습니다.",
    ideal: [88, 45, 72, 45, 55, 80, 40, 65],
  },
  {
    type: "BALANCE",
    label: "균형형",
    summary: "강점은 유지하면서 약한 축을 고르게 보완해 균형을 잡는 방향.",
    detail:
      "탐색·자율 같은 강점은 그대로 유지하면서 분석·실행·사회성 등 부족한 축을 고르게 보완합니다. " +
      "특정 방향으로 치우치지 않고 전반적으로 안정적인 소비 습관을 만들고 싶을 때 적합합니다.",
    ideal: [72, 62, 62, 62, 58, 68, 60, 62],
  },
];

/** 제안을 RadarCompareChart용 IdealAxis[] (현재 vs 이상향)로 변환 */
export function proposalToAxes(p: IdealProposal): IdealAxis[] {
  return SETUP_AXIS_LABELS.map((label, i) => ({
    label,
    current: MOCK_SETUP_CURRENT[i],
    ideal: p.ideal[i],
  }));
}
