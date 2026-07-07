import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Grid3x3, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { fetchHeatmapData, type HeatmapData } from "@/services/reporter";

const HOUR_LABELS = Array.from({ length: 24 }, (_, hour) =>
  hour % 3 === 0 ? `${hour}` : "",
);

function cellOpacity(count: number, maxCount: number): number {
  if (maxCount <= 0 || count <= 0) return 0.04;
  const ratio = count / maxCount;
  return 0.12 + ratio * 0.88;
}

export function TrendHeatmap() {
  const [data, setData] = useState<HeatmapData>({
    days: 7,
    day_labels: ["월", "화", "수", "목", "금", "토", "일"],
    matrix: [],
    max_count: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<{
    day: number;
    hour: number;
    count: number;
  } | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchHeatmapData();
      setData(result);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "히트맵 데이터를 불러오지 못했습니다.";
      setError(message);
      setData({
        days: 7,
        day_labels: ["월", "화", "수", "목", "금", "토", "일"],
        matrix: [],
        max_count: 0,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const isEmpty = useMemo(
    () => !loading && !error && data.max_count === 0,
    [loading, error, data.max_count],
  );

  return (
    <div className="border-border bg-card rounded-2xl border p-4 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Grid3x3 className="text-muted-foreground size-4" />
          <div>
            <p className="text-sm font-semibold">활동 타임 히트맵</p>
            <p className="text-muted-foreground text-xs">
              최근 {data.days}일 · 행동 로그 + 스크랩 요일×시간 빈도
            </p>
          </div>
        </div>
        {hovered && (
          <p className="text-xs text-indigo-300">
            {data.day_labels[hovered.day]}요일 {hovered.hour}시 ·{" "}
            {hovered.count}건
          </p>
        )}
      </div>

      <div className="relative min-h-[280px]">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/80">
            <Loader2 className="size-7 animate-spin text-indigo-400" />
          </div>
        )}

        {error && !loading && (
          <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 text-center">
            <AlertCircle className="size-9 text-rose-400" />
            <p className="text-sm">{error}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => void loadData()}>
              다시 시도
            </Button>
          </div>
        )}

        {isEmpty && (
          <div className="text-muted-foreground flex min-h-[240px] items-center justify-center text-sm">
            최근 7일간 집계된 활동 데이터가 없습니다.
          </div>
        )}

        {!loading && !error && data.matrix.length > 0 && (
          <div className="overflow-x-auto">
            <div className="min-w-[720px]">
              <div className="mb-1 grid grid-cols-[40px_repeat(24,minmax(0,1fr))] gap-1">
                <div />
                {HOUR_LABELS.map((label, hour) => (
                  <div
                    key={hour}
                    className="text-muted-foreground text-center text-[9px]"
                  >
                    {label}
                  </div>
                ))}
              </div>

              {data.matrix.map((row, dayIndex) => (
                <div
                  key={data.day_labels[dayIndex] ?? dayIndex}
                  className="mb-1 grid grid-cols-[40px_repeat(24,minmax(0,1fr))] gap-1"
                >
                  <div className="text-muted-foreground flex items-center text-[10px] font-medium">
                    {data.day_labels[dayIndex] ?? dayIndex}
                  </div>
                  {row.map((count, hour) => {
                    const opacity = cellOpacity(count, data.max_count);
                    const isHovered =
                      hovered?.day === dayIndex && hovered?.hour === hour;
                    return (
                      <div
                        key={`${dayIndex}-${hour}`}
                        title={`${data.day_labels[dayIndex]} ${hour}시 · ${count}건`}
                        className={cn(
                          "aspect-square rounded-[3px] border border-transparent transition-transform",
                          isHovered && "scale-110 border-indigo-300/50",
                        )}
                        style={{
                          backgroundColor: `rgba(99, 102, 241, ${opacity})`,
                          boxShadow:
                            count > 0
                              ? `0 0 ${Math.max(2, opacity * 10)}px rgba(129,140,248,${opacity * 0.6})`
                              : undefined,
                        }}
                        onMouseEnter={() =>
                          setHovered({ day: dayIndex, hour, count })
                        }
                        onMouseLeave={() => setHovered(null)}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2">
        <span className="text-muted-foreground text-[10px]">낮음</span>
        <div className="h-2 flex-1 rounded-full bg-gradient-to-r from-indigo-500/10 via-indigo-500/50 to-indigo-400" />
        <span className="text-muted-foreground text-[10px]">높음</span>
        <span className="text-muted-foreground ml-2 text-[10px]">
          max {data.max_count}
        </span>
      </div>
    </div>
  );
}
