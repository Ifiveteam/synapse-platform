"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { ProfileAxis } from "@/lib/api/trend";
import { cn } from "@/lib/utils";

interface RadarDatum {
  key: string;
  label: string;
  avg_score: number;
}

interface CognitiveChartProps {
  axes: ProfileAxis[];
  cohortSize?: number;
  className?: string;
}

interface AxisTickProps {
  x?: number;
  y?: number;
  payload?: { value: string };
}

function AxisTick({ x = 0, y = 0, payload }: AxisTickProps) {
  if (!payload?.value) return null;

  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="central"
      className="fill-foreground text-[11px] font-medium sm:text-xs"
    >
      {payload.value}
    </text>
  );
}

export function CognitiveChart({
  axes,
  cohortSize,
  className,
}: CognitiveChartProps) {
  const data: RadarDatum[] = axes.map((axis) => ({
    key: axis.key,
    label: axis.label,
    avg_score: axis.avg_score,
  }));

  return (
    <div className={cn("flex w-full flex-col gap-3", className)}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">8각 인지 성향 균형도</h3>
        {cohortSize !== undefined && (
          <p className="text-muted-foreground text-xs">
            분석 대상 {cohortSize.toLocaleString("ko-KR")}명
          </p>
        )}
      </div>

      <div className="bg-muted/30 h-[340px] w-full rounded-xl border p-2 sm:h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="68%" data={data}>
            <PolarGrid
              stroke="var(--border)"
              strokeOpacity={0.8}
              gridType="polygon"
            />
            <PolarAngleAxis
              dataKey="label"
              tick={<AxisTick />}
              tickLine={false}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tickCount={5}
              tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
              axisLine={false}
            />
            <Radar
              name="평균 점수"
              dataKey="avg_score"
              stroke="var(--primary)"
              fill="var(--primary)"
              fillOpacity={0.22}
              strokeWidth={2}
            />
            <Tooltip
              formatter={(value) => {
                const score = typeof value === "number" ? value : Number(value);
                return [`${Number.isFinite(score) ? score.toFixed(1) : "-"}점`, "평균"];
              }}
              labelFormatter={(label) => String(label)}
              contentStyle={{
                borderRadius: "0.5rem",
                border: "1px solid var(--border)",
                backgroundColor: "var(--card)",
                color: "var(--card-foreground)",
                fontSize: "0.75rem",
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
