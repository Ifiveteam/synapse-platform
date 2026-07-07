import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Loader2, Waves } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  fetchStreamGraphData,
  type StreamChartData,
} from "@/services/reporter";

const StreamChartView = lazy(() =>
  import("@/pages/reporter/TrendStreamChartView").then((m) => ({
    default: m.TrendStreamChartView,
  })),
);

const DOMAIN_KEYS = [
  "Tech/Business",
  "Content/Media",
  "Lifestyle/Wellness",
  "Social/Current Affairs",
  "Knowledge/Education",
  "Economy/TechFin",
] as const;

const DOMAIN_COLORS: Record<string, string> = {
  "Tech/Business": "#38bdf8",
  "Content/Media": "#f472b6",
  "Lifestyle/Wellness": "#4ade80",
  "Social/Current Affairs": "#fb923c",
  "Knowledge/Education": "#a78bfa",
  "Economy/TechFin": "#facc15",
};

const AXIS_KEYS = [
  "exploration",
  "analytical",
  "creativity",
  "execution",
  "achievement_drive",
  "autonomy",
  "sociality",
  "sensitivity",
] as const;

const AXIS_LABELS: Record<string, string> = {
  exploration: "탐색",
  analytical: "분석",
  creativity: "창의",
  execution: "실행",
  achievement_drive: "성취",
  autonomy: "자율",
  sociality: "사회성",
  sensitivity: "감수성",
};

const AXIS_COLORS = [
  "#818cf8",
  "#38bdf8",
  "#34d399",
  "#fbbf24",
  "#fb7185",
  "#a78bfa",
  "#22d3ee",
  "#f472b6",
];

function ChartFallback() {
  return (
    <div className="flex h-[360px] items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      차트 로딩 중…
    </div>
  );
}

interface TrendStreamGraphProps {
  selectedDate: string;
}

export function TrendStreamGraph({ selectedDate }: TrendStreamGraphProps) {
  const [rangeDays, setRangeDays] = useState<7 | 30>(7);
  const [chartData, setChartData] = useState<StreamChartData>({
    start_date: selectedDate,
    end_date: selectedDate,
    series: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(
    async (endDate: string, range: 7 | 30) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchStreamGraphData(endDate, range);
        setChartData(data);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "스트림 차트 데이터를 불러오지 못했습니다.";
        setError(message);
        setChartData({ start_date: endDate, end_date: endDate, series: [] });
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadData(selectedDate, rangeDays);
  }, [selectedDate, rangeDays, loadData]);

  const rechartsData = useMemo(() => {
    return chartData.series.map((point) => {
      const label = point.date.slice(5).replace("-", "/");
      const row: Record<string, string | number> = { label, date: point.date };
      for (const key of DOMAIN_KEYS) {
        row[key] = point.domains[key] ?? 0;
      }
      for (const axis of AXIS_KEYS) {
        row[axis] = point.axes[axis] ?? 0;
      }
      return row;
    });
  }, [chartData.series]);

  const isEmpty = !loading && !error && chartData.series.length === 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="border-border bg-card rounded-2xl border p-4 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Waves className="text-muted-foreground size-4" />
            <div>
              <p className="text-sm font-semibold">도메인 스트림그래프</p>
              <p className="text-muted-foreground text-xs">
                {chartData.start_date} ~ {chartData.end_date} · 일별 도메인
                가중치 추이
              </p>
            </div>
          </div>
          <div className="bg-muted inline-flex rounded-lg p-0.5">
            {([7, 30] as const).map((days) => (
              <button
                key={days}
                type="button"
                onClick={() => setRangeDays(days)}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                  rangeDays === days
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {days}일
              </button>
            ))}
          </div>
        </div>

        <div className="relative min-h-[360px]">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/80">
              <Loader2 className="size-7 animate-spin text-indigo-400" />
            </div>
          )}
          {error && !loading && (
            <div className="flex min-h-[320px] flex-col items-center justify-center gap-3 text-center">
              <AlertCircle className="size-9 text-rose-400" />
              <p className="text-sm">{error}</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void loadData(selectedDate, rangeDays)}
              >
                다시 시도
              </Button>
            </div>
          )}
          {isEmpty && (
            <div className="text-muted-foreground flex min-h-[320px] items-center justify-center text-sm">
              선택 기간에 스냅샷 데이터가 없습니다.
            </div>
          )}
          {!loading && !error && rechartsData.length > 0 && (
            <Suspense fallback={<ChartFallback />}>
              <StreamChartView
                data={rechartsData}
                domainKeys={[...DOMAIN_KEYS]}
                domainColors={DOMAIN_COLORS}
              />
            </Suspense>
          )}
        </div>
      </div>

      <div className="border-border bg-card rounded-2xl border p-4 shadow-sm">
        <p className="mb-3 text-sm font-semibold">플랫폼 8축 평균 추이</p>
        {!loading && !error && rechartsData.length > 0 && (
          <Suspense fallback={<ChartFallback />}>
            <StreamChartView
              data={rechartsData}
              domainKeys={[...AXIS_KEYS]}
              domainColors={Object.fromEntries(
                AXIS_KEYS.map((key, i) => [key, AXIS_COLORS[i]]),
              )}
              labels={AXIS_LABELS}
              height={280}
            />
          </Suspense>
        )}
        {isEmpty && (
          <p className="text-muted-foreground py-8 text-center text-sm">
            8축 데이터가 없습니다.
          </p>
        )}
      </div>
    </div>
  );
}
