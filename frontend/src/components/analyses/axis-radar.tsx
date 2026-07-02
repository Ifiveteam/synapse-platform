import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

export interface AxisDatum {
  axis: string;
  value: number;
}

function AxisTooltip({
  active,
  payload,
  suffix,
}: {
  active?: boolean;
  payload?: Array<{ payload: { axis: string; raw: number } }>;
  suffix?: string;
}) {
  if (!active || !payload?.[0]) return null;
  const { axis, raw } = payload[0].payload;
  return (
    <div className="border-border rounded-lg border bg-card px-2.5 py-1.5 text-xs shadow-sm">
      <p className="font-medium">{axis}</p>
      <p className="text-muted-foreground">
        <span className="text-foreground font-semibold tabular-nums">{raw}</span>
        {suffix}
      </p>
    </div>
  );
}

/** 임의의 축 목록을 받는 제네릭 레이더 (관심사·성향 공용).
 *  normalize=true면 최댓값을 100으로 스케일해 모양을 채운다(원본은 툴팁). */
export function AxisRadar({
  data,
  color = "#7c3aed",
  normalize = false,
  tooltipSuffix,
}: {
  data: AxisDatum[];
  color?: string;
  normalize?: boolean;
  tooltipSuffix?: string;
}) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const chartData = data.map((d) => ({
    axis: d.axis,
    value: normalize ? Math.round((d.value / max) * 1000) / 10 : d.value,
    raw: d.value,
  }));
  return (
    <div className="h-[min(320px,42vw)] w-full min-w-[260px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={chartData} cx="50%" cy="50%" outerRadius="68%">
          <PolarGrid gridType="polygon" radialLines stroke="#d4d4d8" strokeWidth={1} />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: "#71717a" }} />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            axisLine={false}
            tick={{ fontSize: 9, fill: "#a1a1aa" }}
            tickFormatter={(v) => (v === 0 ? "" : String(v))}
          />
          <Tooltip content={<AxisTooltip suffix={tooltipSuffix} />} />
          <Radar
            name="값"
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.22}
            strokeWidth={2.5}
            dot={{ r: 3, fill: color, strokeWidth: 0 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
