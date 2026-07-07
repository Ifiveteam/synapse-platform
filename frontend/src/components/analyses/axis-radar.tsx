import { memo, useCallback, useMemo, useState } from "react";

import { cn } from "@/lib/utils";
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

interface HoverState {
  label: string;
  x: number;
  y: number;
}

interface ChartRow {
  axis: string;
  value: number;
  raw: number;
}

/** 축 라벨 커스텀 틱 — 설명이 있으면 hover 시 커스텀 말풍선으로 노출. */
function AxisTick(props: {
  x?: number;
  y?: number;
  textAnchor?: "start" | "middle" | "end" | "inherit";
  payload?: { value: string };
  descriptions?: Record<string, string>;
  onHover?: (h: HoverState) => void;
  onLeave?: () => void;
}) {
  const { x, y, textAnchor, payload, descriptions, onHover, onLeave } = props;
  const label = payload?.value ?? "";
  const desc = descriptions?.[label];
  return (
    <text
      x={x}
      y={y}
      textAnchor={textAnchor}
      dominantBaseline="central"
      fontSize={11}
      fill="#71717a"
      onMouseEnter={
        desc ? () => onHover?.({ label, x: x ?? 0, y: y ?? 0 }) : undefined
      }
      onMouseLeave={desc ? () => onLeave?.() : undefined}
    >
      {label}
    </text>
  );
}

/** 차트 본체 — hover 상태와 무관한 props만 받아 memo. 라벨 hover로 인한
 *  부모 리렌더 시 차트 DOM이 재생성되지 않도록 격리한다(라벨 깜빡임 방지). */
const RadarInner = memo(function RadarInner({
  chartData,
  color,
  tooltipSuffix,
  axisDescriptions,
  outerRadius,
  onHover,
  onLeave,
}: {
  chartData: ChartRow[];
  color: string;
  tooltipSuffix?: string;
  axisDescriptions?: Record<string, string>;
  outerRadius: string;
  onHover: (h: HoverState) => void;
  onLeave: () => void;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart data={chartData} cx="50%" cy="50%" outerRadius={outerRadius}>
        <PolarGrid gridType="polygon" radialLines stroke="#d4d4d8" strokeWidth={1} />
        <PolarAngleAxis
          dataKey="axis"
          tick={
            axisDescriptions ? (
              <AxisTick
                descriptions={axisDescriptions}
                onHover={onHover}
                onLeave={onLeave}
              />
            ) : (
              { fontSize: 11, fill: "#71717a" }
            )
          }
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          axisLine={false}
          tick={false}
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
          isAnimationActive={!axisDescriptions}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
});

/** 임의의 축 목록을 받는 제네릭 레이더 (관심사·성향 공용).
 *  normalize=true면 최댓값을 100으로 스케일해 모양을 채운다(원본은 툴팁).
 *  axisDescriptions 지정 시 축 라벨에 커서를 올리면 설명 말풍선이 뜬다. */
export function AxisRadar({
  data,
  color = "#7c3aed",
  normalize = false,
  tooltipSuffix,
  axisDescriptions,
  compact = false,
}: {
  data: AxisDatum[];
  color?: string;
  normalize?: boolean;
  tooltipSuffix?: string;
  axisDescriptions?: Record<string, string>;
  /** 여백을 줄이고 높이를 낮춘 컴팩트 모드 */
  compact?: boolean;
}) {
  const [hover, setHover] = useState<HoverState | null>(null);

  const chartData = useMemo<ChartRow[]>(() => {
    const max = Math.max(1, ...data.map((d) => d.value));
    return data.map((d) => ({
      axis: d.axis,
      value: normalize ? Math.round((d.value / max) * 1000) / 10 : d.value,
      raw: d.value,
    }));
  }, [data, normalize]);

  const handleHover = useCallback((h: HoverState) => setHover(h), []);
  const handleLeave = useCallback(() => setHover(null), []);

  const hoverDesc = hover ? axisDescriptions?.[hover.label] : undefined;

  return (
    <div
      className={cn(
        "relative w-full min-w-[260px]",
        compact ? "h-[min(264px,34vw)]" : "h-[min(320px,42vw)]",
      )}
    >
      <RadarInner
        chartData={chartData}
        color={color}
        tooltipSuffix={tooltipSuffix}
        axisDescriptions={axisDescriptions}
        outerRadius={compact ? "80%" : "68%"}
        onHover={handleHover}
        onLeave={handleLeave}
      />

      {hover && hoverDesc && (
        <div
          className="border-border bg-card pointer-events-none absolute z-10 max-w-[180px] rounded-lg border px-2.5 py-1.5 text-xs shadow-md"
          style={{
            left: hover.x,
            top: hover.y,
            transform: "translate(-50%, calc(-100% - 8px))",
          }}
        >
          <p className="font-medium">{hover.label}</p>
          <p className="text-muted-foreground leading-snug">{hoverDesc}</p>
        </div>
      )}
    </div>
  );
}
