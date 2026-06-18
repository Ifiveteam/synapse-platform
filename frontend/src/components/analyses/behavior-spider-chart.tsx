import {

  PolarAngleAxis,

  PolarGrid,

  PolarRadiusAxis,

  Radar,

  RadarChart,

  ResponsiveContainer,

  Tooltip,

} from "recharts";



import { behaviorSpiderChartData } from "@/lib/analyses/behavior-spider";



const GRID_STROKE = "#d4d4d8";

const TICK_FILL = "#a1a1aa";

const RADIUS_TICKS = [0, 25, 50, 75, 100];



interface BehaviorSpiderChartProps {

  scores: Record<string, number>;

  className?: string;

}



function SpiderTooltip({

  active,

  payload,

}: {

  active?: boolean;

  payload?: Array<{ payload: { axis: string; value: number } }>;

}) {

  if (!active || !payload?.[0]) return null;

  const { axis, value } = payload[0].payload;

  return (

    <div className="border-border rounded-lg border bg-card px-2.5 py-1.5 text-xs shadow-sm">

      <p className="font-medium">{axis}</p>

      <p className="text-muted-foreground">

        점수{" "}

        <span className="text-foreground font-semibold tabular-nums">{value}</span>

      </p>

    </div>

  );

}



export function BehaviorSpiderChart({ scores, className }: BehaviorSpiderChartProps) {

  const items = behaviorSpiderChartData(scores);



  return (

    <div className={className}>

      <div className="mb-1 flex items-baseline justify-between gap-2">

        <p className="text-sm font-semibold">행동 스파이더</p>

        <span className="text-muted-foreground text-[10px]">0~100 절대</span>

      </div>

      <div className="h-[min(340px,42vw)] w-full min-w-[280px] max-w-[380px]">

        <ResponsiveContainer width="100%" height="100%">

          <RadarChart data={items} cx="50%" cy="50%" outerRadius="68%">

            <PolarGrid

              gridType="polygon"

              radialLines

              stroke={GRID_STROKE}

              strokeWidth={1}

            />

            <PolarAngleAxis

              dataKey="axis"

              tick={{ fontSize: 12, fill: "#71717a" }}

            />

            <PolarRadiusAxis

              angle={90}

              domain={[0, 100]}

              ticks={RADIUS_TICKS}

              axisLine={false}

              tick={{ fontSize: 9, fill: TICK_FILL }}

              tickFormatter={(v) => (v === 0 ? "" : String(v))}

            />

            <Tooltip content={<SpiderTooltip />} />

            <Radar

              name="점수"

              dataKey="value"

              stroke="#7c3aed"

              fill="#7c3aed"

              fillOpacity={0.22}

              strokeWidth={2.5}

              dot={{ r: 3, fill: "#7c3aed", strokeWidth: 0 }}

            />

          </RadarChart>

        </ResponsiveContainer>

      </div>

      <p className="text-muted-foreground mt-1 text-center text-[10px] leading-relaxed">

        눈금 0~100 절대 점수 · 높을수록 해당 행동 성향이 강함

      </p>

    </div>

  );

}


