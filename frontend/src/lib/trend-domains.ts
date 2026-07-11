/** Aggregator 6대 거시 도메인 — 그래프·브리핑 공통 */

export const DOMAIN_HUB_GROUP = "domain_hub";

export const DOMAIN_COLORS: Record<string, string> = {
  "Tech/Business": "#38bdf8",
  "Content/Media": "#f472b6",
  "Lifestyle/Wellness": "#4ade80",
  "Social/Current Affairs": "#fb923c",
  "Knowledge/Education": "#a78bfa",
  "Economy/TechFin": "#facc15",
};

export const DOMAIN_LABELS: Record<string, string> = {
  "Tech/Business": "테크/비즈니스",
  "Content/Media": "콘텐츠/미디어",
  "Lifestyle/Wellness": "라이프/웰니스",
  "Social/Current Affairs": "사회/시사",
  "Knowledge/Education": "지식/교육",
  "Economy/TechFin": "경제/테크핀",
};

export function domainLabel(domainOrGroup: string): string {
  if (domainOrGroup === DOMAIN_HUB_GROUP) return "도메인 허브";
  return DOMAIN_LABELS[domainOrGroup] ?? domainOrGroup;
}

export function domainColor(domainOrGroup: string): string {
  return DOMAIN_COLORS[domainOrGroup] ?? "#94a3b8";
}
