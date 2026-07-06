import type { IdealType } from "@/api/types/navigator";

export const IDEAL_TYPE_LABEL: Record<IdealType, string> = {
  OPPOSITE: "반대형",
  DEEPEN: "강점심화형",
  BALANCE: "균형형",
  CUSTOM: "맞춤형",
};

/** 유형별 의도 — 카드에 표시할 한 문장 설명. */
export const IDEAL_TYPE_DESC: Record<IdealType, string> = {
  OPPOSITE:
    "익숙한 취향을 정반대로 뒤집어, 지금껏 마주하지 못한 새로운 나를 발견하는 방향",
  DEEPEN:
    "이미 잘하는 것을 끝까지 파고들어, 나만의 전문성과 색깔을 뚜렷하게 굳히는 방향",
  BALANCE:
    "강점은 그대로 살리면서 부족한 면을 자연스럽게 채워, 어느 한쪽에 치우치지 않는 방향",
  CUSTOM: "내가 직접 그린 목표에 맞춰 처음부터 설계하는 나만의 이상향",
};

export const AXIS_LABELS: Record<string, string> = {
  exploration: "탐색",
  analytical: "분석",
  creativity: "창의",
  execution: "실행",
  achievement_drive: "성취동기",
  autonomy: "자율",
  sociality: "사회성",
  sensitivity: "감수성",
};
