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

// 9개 관심사 도메인용 팔레트
const COLORS = [
  "#7c3aed",
  "#2563eb",
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
  "#8b5cf6",
  "#14b8a6",
];

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

/** 관심사 도메인 비율을 도넛(원) 그래프로 표시. size 지정 시 고정 높이(컴팩트). */
export function InterestPie({
  data,
  size,
}: {
  data: InterestDatum[];
  size?: number;
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
            innerRadius="45%"
            outerRadius="72%"
            paddingAngle={2}
            stroke="none"
          >
            {chartData.map((d, i) => (
              <Cell key={d.axis} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<PieTooltip total={total} />} />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11 }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
