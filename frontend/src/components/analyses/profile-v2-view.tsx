import { Badge } from "@/components/ui/badge";

import { AxisRadar, type AxisDatum } from "./axis-radar";

/** V2 실험 화면 — 백엔드 연동 전이라 예시(mock) 데이터로 레이아웃만 확인. */
const MOCK = {
  persona:
    "KBO 두산베어스 열혈팬이자 가면라이더 특촬물에 빠진 숏폼 콘텐츠 마니아",
  keywords: [
    "KBO 두산베어스 열성팬",
    "가면라이더 특촬물 마니아",
    "BJ 감스트 팬덤",
    "숏폼 스포츠 하이라이트",
    "야구 레전드 명장면",
    "서브컬처 클립 소비",
  ],
  interest: [
    { axis: "스포츠", value: 35 },
    { axis: "게임", value: 8 },
    { axis: "음악", value: 2 },
    { axis: "예능", value: 15 },
    { axis: "인물·일상", value: 29 },
    { axis: "영화·애니", value: 10 },
    { axis: "뉴스·시사", value: 1 },
    { axis: "지식·교육", value: 1 },
    { axis: "라이프", value: 1 },
  ] as AxisDatum[],
  disposition: [
    { axis: "몰입", value: 70 },
    { axis: "탐험", value: 30 },
    { axis: "팬덤", value: 95 },
    { axis: "트렌드", value: 80 },
    { axis: "정보", value: 55 },
    { axis: "감성", value: 85 },
  ] as AxisDatum[],
  style: [
    { label: "숏폼 비율", value: 62 },
    { label: "채널 집중도", value: 6 },
    { label: "관심 다양성", value: 70 },
    { label: "반복 시청", value: 12 },
  ],
};

export function ProfileV2View() {
  return (
    <div className="flex flex-col gap-6 pb-4">
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
        ⚗️ V2 실험 화면 — 예시(mock) 데이터입니다. 백엔드 연동 전 레이아웃 확인용.
      </div>

      {/* 별칭 + 키워드 */}
      <div className="rounded-2xl border bg-card p-5">
        <p className="text-muted-foreground mb-1 text-xs font-medium">이런 사람이에요</p>
        <p className="text-primary text-lg font-semibold">{MOCK.persona}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {MOCK.keywords.map((k) => (
            <Badge
              key={k}
              variant="secondary"
              className="rounded-full px-3 py-1 text-sm"
            >
              #{k}
            </Badge>
          ))}
        </div>
      </div>

      {/* 레이더 2종 */}
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="border-border flex-1 rounded-2xl border bg-card p-5">
          <div className="mb-1 flex items-baseline justify-between">
            <p className="text-sm font-semibold">관심사 레이더</p>
            <span className="text-muted-foreground text-[10px]">도메인 비율 %</span>
          </div>
          <AxisRadar data={MOCK.interest} color="#7c3aed" />
          <p className="text-muted-foreground mt-1 text-center text-[10px]">
            무엇을 보나 — 카테고리 기반 (결정적)
          </p>
        </div>
        <div className="border-border flex-1 rounded-2xl border bg-card p-5">
          <div className="mb-1 flex items-baseline justify-between">
            <p className="text-sm font-semibold">성향 스파이더</p>
            <span className="text-muted-foreground text-[10px]">0~100</span>
          </div>
          <AxisRadar data={MOCK.disposition} color="#0ea5e9" />
          <p className="text-muted-foreground mt-1 text-center text-[10px]">
            어떤 소비 성향인가 — 태그·채널·포맷 기반 (LLM)
          </p>
        </div>
      </div>

      {/* 소비 스타일 */}
      <div className="border-border rounded-2xl border bg-card p-5">
        <p className="mb-3 text-sm font-semibold">소비 스타일</p>
        <div className="space-y-2.5">
          {MOCK.style.map((s) => (
            <div key={s.label}>
              <div className="mb-1 flex justify-between text-xs">
                <span>{s.label}</span>
                <span className="text-muted-foreground tabular-nums">{s.value}</span>
              </div>
              <div className="bg-muted h-2 rounded-full">
                <div
                  className="bg-primary h-2 rounded-full"
                  style={{ width: `${s.value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
