import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { cn } from "@/lib/utils";

export interface InterestDatum {
  axis: string;
  value: number;
}

// 9개 관심사 도메인용 팔레트 — 서로 뚜렷이 구분되고 인접 인덱스끼리도 색상이 멀도록 교차 배치
const COLORS = [
  "#3b82f6", // 파랑
  "#f59e0b", // 주황
  "#10b981", // 초록
  "#ec4899", // 분홍
  "#eab308", // 노랑
  "#8b5cf6", // 보라
  "#06b6d4", // 청록
  "#ef4444", // 빨강
  "#84cc16", // 라임
];

// 도메인마다 색을 고정 — 분석·이상향·설계 등 모든 화면에서 같은 도메인 = 같은 색.
// (값 순위가 아니라 도메인명 기준이라, 현재/이상향 도넛과 범례가 항상 일치)
const DOMAIN_ORDER = [
  "스포츠",
  "인물·일상",
  "예능",
  "영화·애니",
  "게임",
  "음악",
  "라이프·취미",
  "뉴스·시사",
  "지식·교육",
];
function colorForDomain(axis: string, fallbackIndex: number): string {
  const i = DOMAIN_ORDER.indexOf(axis);
  return COLORS[(i >= 0 ? i : fallbackIndex) % COLORS.length];
}

export interface InterestLegendItem {
  axis: string;
  value: number;
  pct: number;
  color: string;
}

/** 도넛과 동일한 필터·색상 순서로 범례 항목을 만든다 (별도 박스 렌더용). */
export function buildInterestLegend(data: InterestDatum[]): InterestLegendItem[] {
  const chartData = data.filter((d) => d.value > 0);
  const total = chartData.reduce((s, d) => s + d.value, 0);
  return chartData.map((d, i) => ({
    axis: d.axis,
    value: d.value,
    pct: total > 0 ? Math.round((d.value / total) * 100) : 0,
    color: colorForDomain(d.axis, i),
  }));
}

function PieTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean;
  payload?: Array<{ payload: { axis: string; value: number } }>;
  total: number;
}) {
  if (!active || !payload?.[0]) return null;
  const { axis, value } = payload[0].payload;
  const pct = total > 0 ? Math.round((value / total) * 1000) / 10 : 0;
  return (
    <div className="border-border rounded-lg border bg-card px-2.5 py-1.5 text-xs shadow-sm">
      <p className="font-medium">{axis}</p>
      <p className="text-muted-foreground">
        <span className="text-foreground font-semibold tabular-nums">{pct}</span>%
      </p>
    </div>
  );
}

/** 관심사 도메인 비율을 도넛(원) 그래프로 표시. size 지정 시 고정 높이(컴팩트).
 *  innerRadius/outerRadius로 도넛 크기(=여백)를 조절할 수 있다. */
export function InterestPie({
  data,
  size,
  showLegend = true,
  innerRadius = "45%",
  outerRadius = "72%",
}: {
  data: InterestDatum[];
  size?: number;
  showLegend?: boolean;
  innerRadius?: string | number;
  outerRadius?: string | number;
}) {
  const chartData = data.filter((d) => d.value > 0);
  const total = chartData.reduce((s, d) => s + d.value, 0);

  if (chartData.length === 0) {
    return (
      <div
        className={cn(
          "text-muted-foreground flex items-center justify-center text-xs",
          !size && "h-[min(320px,42vw)]",
        )}
        style={size ? { height: size } : undefined}
      >
        데이터 없음
      </div>
    );
  }

  return (
    <div
      className={size ? "w-full" : "h-[min(320px,42vw)] w-full min-w-[260px]"}
      style={size ? { height: size } : undefined}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="axis"
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            stroke="none"
          >
            {chartData.map((d, i) => (
              <Cell key={d.axis} fill={colorForDomain(d.axis, i)} />
            ))}
          </Pie>
          <Tooltip content={<PieTooltip total={total} />} />
          {showLegend && (
            <Legend
              verticalAlign="bottom"
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11 }}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
