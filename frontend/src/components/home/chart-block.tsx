import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ChartEntry, RankItem, VideoItem } from "@/stores/chat";

const BAR_COLORS = [
  "hsl(220, 70%, 55%)",
  "hsl(235, 65%, 58%)",
  "hsl(250, 60%, 60%)",
  "hsl(265, 55%, 62%)",
  "hsl(280, 50%, 62%)",
  "hsl(200, 65%, 55%)",
];

function VideoList({ items, title }: { items: VideoItem[]; title: string }) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <div className="flex max-h-52 flex-col gap-1.5 overflow-y-auto pr-1">
        {items.map((item, i) => (
          <div key={i} className="rounded-lg bg-muted/60 px-3 py-2">
            <p className="truncate text-xs font-medium">{item.title}</p>
            <p className="truncate text-[11px] text-muted-foreground">{item.channel}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function HorizontalBarChart({ items, title }: { items: RankItem[]; title: string }) {
  const height = Math.max(items.length * 40 + 8, 60);
  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart layout="vertical" data={items} margin={{ left: 0, right: 24, top: 0, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={110}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            formatter={(v) => [`${v}개`, "시청"]}
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
            {items.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ChartBlock({ charts }: { charts: ChartEntry[] }) {
  if (!charts.length) return null;

  return (
    <div className="mb-2 flex flex-col gap-4 rounded-xl border border-border/60 bg-muted/20 p-3">
      {charts.map((chart, i) => {
        if (chart.type === "video_list" || chart.type === "shorts_list") {
          return <VideoList key={i} items={chart.items} title={chart.title} />;
        }
        return (
          <HorizontalBarChart key={i} items={chart.items} title={chart.title} />
        );
      })}
    </div>
  );
}
