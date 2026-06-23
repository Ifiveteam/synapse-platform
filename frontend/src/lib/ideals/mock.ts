export interface IdealProfile {
  id: string;
  name: string;
  subtitle: string;
  createdAt: string;
  tags: string[];
  isActive?: boolean;
}

export const MOCK_IDEAL_PROFILES: IdealProfile[] = [
  {
    id: "a",
    name: "이상향 A",
    subtitle: "기술·경제 탐구형",
    createdAt: "2024.03.01",
    tags: ["정보탐색", "지식습득", "기타"],
    isActive: true,
  },
  {
    id: "b",
    name: "이상향 B",
    subtitle: "감성 콘텐츠 중심",
    createdAt: "2024.02.15",
    tags: ["정서·위로", "창의·표현", "기타"],
  },
  {
    id: "c",
    name: "이상향 C",
    subtitle: "균형 잡힌 생활",
    createdAt: "2024.01.28",
    tags: ["자기계발", "실용 지향", "기타"],
  },
];
