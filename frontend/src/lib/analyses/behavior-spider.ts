/** 행동 스파이더 8축 */



export const BEHAVIOR_SPIDER_AXES = [

  { key: "exploration", label: "탐색" },

  { key: "analytical", label: "분석" },

  { key: "creativity", label: "창의" },

  { key: "execution", label: "실행" },

  { key: "achievement_drive", label: "성취" },

  { key: "autonomy", label: "자율" },

  { key: "sociality", label: "사회성" },

  { key: "sensitivity", label: "감수성" },

] as const;



export interface BehaviorSpiderPoint {

  key: string;

  axis: string;

  value: number;

}



export function behaviorSpiderChartData(

  scores: Record<string, number>,

): BehaviorSpiderPoint[] {

  return BEHAVIOR_SPIDER_AXES.map(({ key, label }) => ({

    key,

    axis: label,

    value: Math.round(Math.max(0, Math.min(100, scores[key] ?? 0))),

  }));

}


