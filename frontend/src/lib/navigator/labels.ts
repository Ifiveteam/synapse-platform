import type { IdealType } from "@/api/types/navigator";

export const IDEAL_TYPE_LABEL: Record<IdealType, string> = {
  OPPOSITE: "반대형",
  DEEPEN: "강점심화형",
  BALANCE: "균형형",
  CUSTOM: "맞춤형",
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
