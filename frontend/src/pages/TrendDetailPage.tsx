import { useState } from "react";
import { Search } from "lucide-react";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  MOCK_CARD_NEWS,
  MOCK_CHART_SERIES,
  MOCK_NEWS_FEED,
  MOCK_TOP_KEYWORDS,
  MOCK_TOP_TRENDS,
  MOCK_TREND_INDEX_POINTS,
  TREND_CATEGORIES,
  type TrendCategory,
} from "@/lib/trends/mock";

function KeywordNewsChart() {
  const w = 520;
  const h = 200;
  const offsets = [0, -10, -18];

  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-48 w-full" aria-hidden>
        {MOCK_CHART_SERIES.map(({ color }, idx) => {
          const values = MOCK_TREND_INDEX_POINTS.map((v) => v + offsets[idx]);
          const max = Math.max(...values);
          const min = Math.min(...values);
          const coords = values
            .map((v, i) => {
              const x = 24 + (i / (values.length - 1)) * (w - 48);
              const y = h - 28 - ((v - min) / (max - min || 1)) * (h - 56);
              return `${x},${y}`;
            })
            .join(" ");
          return (
            <polyline
              key={color}
              points={coords}
              fill="none"
              stroke={color}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          );
        })}
      </svg>
      <div className="mt-2 flex flex-wrap gap-4 px-1">
        {MOCK_CHART_SERIES.map(({ label, color }) => (
          <div key={label} className="flex items-center gap-1.5 text-xs">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-muted-foreground">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RankedList({
  title,
  items,
}: {
  title: string;
  items: readonly string[];
}) {
  return (
    <div className="border-border rounded-2xl border bg-card p-4">
      <p className="mb-3 text-sm font-semibold">{title}</p>
      <ol className="space-y-2.5">
        {items.map((item, i) => (
          <li key={item} className="flex items-center gap-3 text-sm">
            <span className="bg-accent text-accent-foreground flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-semibold">
              {i + 1}
            </span>
            <span className="truncate">{item}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function TrendDetailPage() {
  const [category, setCategory] = useState<TrendCategory>("all");

  return (
    <div className="mx-auto flex min-h-full max-w-6xl flex-col px-6 py-8">
      <div className="mb-6 grid gap-4 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:items-center">
        <h1 className="text-primary text-2xl font-semibold tracking-tight">
          트렌드
        </h1>

        <div className="relative min-w-0">
          <Search
            size={16}
            className="text-muted-foreground absolute top-1/2 left-4 -translate-y-1/2"
          />
          <input
            type="search"
            placeholder="트렌드 키워드를 검색하세요..."
            className="border-border bg-card h-11 w-full rounded-full border pr-4 pl-10 text-sm outline-none"
          />
        </div>

        <Tabs
          value={category}
          onValueChange={(v) => setCategory(v as TrendCategory)}
          className="gap-0"
        >
          <TabsList className="h-9 bg-transparent p-0">
            {TREND_CATEGORIES.map(({ id, label }) => (
              <TabsTrigger
                key={id}
                value={id}
                className="rounded-full px-4 text-xs shadow-none"
              >
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <section className="mb-6">
        <p className="text-muted-foreground mb-3 text-xs font-semibold tracking-widest uppercase">
          Card News
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          {MOCK_CARD_NEWS.map((card) => (
            <article
              key={card.id}
              className="border-border overflow-hidden rounded-2xl border bg-card"
            >
              <div className="bg-secondary/60 h-28" />
              <p className="px-4 py-3 text-sm font-medium">{card.title}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <RankedList title="TOP 5 트렌드" items={MOCK_TOP_TRENDS} />
          <RankedList title="TOP 5 키워드" items={MOCK_TOP_KEYWORDS} />
        </div>

        <div className="flex flex-col gap-4">
          <div className="border-border rounded-2xl border bg-card p-4">
            <p className="mb-3 text-sm font-semibold">키워드 뉴스 변화</p>
            <div className="border-border rounded-xl border bg-background px-3 py-2">
              <KeywordNewsChart />
            </div>
          </div>

          <div className="border-border rounded-2xl border bg-card p-4">
            <p className="mb-3 text-sm font-semibold">최신 뉴스/사항</p>
            <ul className="divide-border divide-y">
              {MOCK_NEWS_FEED.map((item) => (
                <li
                  key={item.id}
                  className="hover:bg-secondary/50 flex items-start justify-between gap-4 rounded-lg px-1 py-3 transition-colors"
                >
                  <p className="min-w-0 flex-1 text-sm leading-snug">
                    {item.title}
                  </p>
                  <time className="text-muted-foreground shrink-0 text-xs">
                    {item.date}
                  </time>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
