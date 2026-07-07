import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface TrendStreamChartViewProps {
  data: Record<string, string | number>[];
  domainKeys: string[];
  domainColors: Record<string, string>;
  labels?: Record<string, string>;
  height?: number;
}

export function TrendStreamChartView({
  data,
  domainKeys,
  domainColors,
  labels,
  height = 360,
}: TrendStreamChartViewProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          {domainKeys.map((key) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={domainColors[key]} stopOpacity={0.75} />
              <stop offset="95%" stopColor={domainColors[key]} stopOpacity={0.12} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            fontSize: 12,
            borderRadius: 10,
            border: "1px solid rgba(148,163,184,0.25)",
            background: "rgba(15,23,42,0.92)",
            color: "#e2e8f0",
          }}
          formatter={(value, name) => [
            Number(value ?? 0).toFixed(3),
            labels?.[String(name)] ?? String(name),
          ]}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(value) => labels?.[value] ?? value}
        />
        {domainKeys.map((key) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stackId="1"
            stroke={domainColors[key]}
            fill={`url(#grad-${key})`}
            strokeWidth={1.5}
            isAnimationActive
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
