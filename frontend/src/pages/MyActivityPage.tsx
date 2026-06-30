import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Clock, Globe, Loader2, Timer } from "lucide-react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import {
  fetchBehaviorEvents,
  fetchTodayBehaviorStats,
  type BehaviorLogItem,
  type TodayStats,
} from "@/api/tracking";
import { ApiError } from "@/api/client";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 4_000;

const PIE_COLORS = [
  "hsl(220, 70%, 55%)",
  "hsl(235, 65%, 58%)",
  "hsl(250, 60%, 60%)",
  "hsl(265, 55%, 62%)",
  "hsl(280, 50%, 62%)",
];

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}초`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes < 60) {
    return rest > 0 ? `${minutes}분 ${rest}초` : `${minutes}분`;
  }
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return remainMinutes > 0 ? `${hours}시간 ${remainMinutes}분` : `${hours}시간`;
}

function formatEventTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function ActivityTimelineItem({ item }: { item: BehaviorLogItem }) {
  return (
    <article className="border-border relative flex gap-3 rounded-xl border bg-card px-4 py-3">
      <div className="bg-accent text-accent-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
        <Globe size={16} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="truncate text-sm font-medium">
            {item.page_title?.trim() || item.domain}
          </p>
          <span className="text-muted-foreground text-xs">
            {formatDuration(item.duration_seconds)}
          </span>
        </div>
        <p className="text-muted-foreground mt-0.5 truncate text-xs">{item.url}</p>
        <div className="text-muted-foreground mt-1.5 flex flex-wrap items-center gap-x-2 text-[11px]">
          <span className="font-medium text-foreground/80">{item.domain}</span>
          <span>·</span>
          <span>{formatEventTime(item.timestamp)}</span>
        </div>
      </div>
    </article>
  );
}

function ActivityFeedPanel({
  items,
  loading,
  error,
}: {
  items: BehaviorLogItem[];
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        활동 피드 불러오는 중…
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-destructive flex flex-1 items-center justify-center p-6 text-center text-sm">
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center p-6 text-center text-sm">
        아직 수집된 활동이 없습니다.
        <br />
        익스텐션을 켜고 웹을 탐색해 보세요.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
      {items.map((item) => (
        <ActivityTimelineItem key={item.id} item={item} />
      ))}
    </div>
  );
}

function TodayStatsPanel({
  stats,
  loading,
  error,
}: {
  stats: TodayStats | null;
  loading: boolean;
  error: string | null;
}) {
  const chartData = useMemo(() => stats?.top_domains ?? [], [stats]);

  if (loading && !stats) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        통계 불러오는 중…
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-destructive flex flex-1 items-center justify-center p-6 text-center text-sm">
        {error}
      </div>
    );
  }

  const totalSeconds = stats?.total_duration_seconds ?? 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div className="border-border rounded-xl border bg-muted/30 px-4 py-4">
        <div className="text-muted-foreground flex items-center gap-2 text-xs font-medium">
          <Timer size={14} />
          오늘 총 웹 서핑 시간
        </div>
        <p className="mt-2 text-2xl font-semibold tracking-tight">
          {formatDuration(totalSeconds)}
        </p>
      </div>

      <div className="min-h-0 flex-1">
        <p className="text-muted-foreground mb-2 text-xs font-semibold tracking-wide uppercase">
          도메인 TOP 5
        </p>
        {chartData.length === 0 ? (
          <div className="text-muted-foreground flex h-48 items-center justify-center rounded-xl border border-dashed text-sm">
            오늘 방문 기록이 없습니다.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={84}
                paddingAngle={2}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={entry.name}
                    fill={PIE_COLORS[index % PIE_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => [formatDuration(Number(value ?? 0)), "체류"]}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}

        {chartData.length > 0 && (
          <ul className="mt-2 space-y-1.5">
            {chartData.map((row, index) => (
              <li
                key={row.name}
                className="flex items-center justify-between gap-2 text-xs"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor: PIE_COLORS[index % PIE_COLORS.length],
                    }}
                  />
                  <span className="truncate">{row.name}</span>
                </span>
                <span className="text-muted-foreground shrink-0">
                  {formatDuration(row.duration_seconds)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function MyActivityPage() {
  const [events, setEvents] = useState<BehaviorLogItem[]>([]);
  const [stats, setStats] = useState<TodayStats | null>(null);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadEvents = useCallback(async (silent = false) => {
    if (!silent) setEventsLoading(true);
    try {
      const items = await fetchBehaviorEvents();
      setEvents(items);
      setEventsError(null);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "활동 피드를 불러오지 못했습니다.";
      setEventsError(message);
    } finally {
      if (!silent) setEventsLoading(false);
    }
  }, []);

  const loadStats = useCallback(async (silent = false) => {
    if (!silent) setStatsLoading(true);
    try {
      const data = await fetchTodayBehaviorStats();
      setStats(data);
      setStatsError(null);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "통계를 불러오지 못했습니다.";
      setStatsError(message);
    } finally {
      if (!silent) setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEvents();
    void loadStats();
  }, [loadEvents, loadStats]);

  useEffect(() => {
    pollingRef.current = setInterval(() => {
      setPolling(true);
      void Promise.all([loadEvents(true), loadStats(true)]).finally(() => {
        setPolling(false);
      });
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [loadEvents, loadStats]);

  return (
    <div className="flex h-full min-h-0 flex-col px-4 py-5 sm:px-6 sm:py-6">
      <header className="mb-4 shrink-0">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-tight">활동 대시보드</h1>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
              polling
                ? "bg-primary/10 text-primary"
                : "bg-muted text-muted-foreground",
            )}
          >
            <Clock size={10} className={polling ? "animate-pulse" : undefined} />
            4초마다 갱신
          </span>
        </div>
        <p className="text-muted-foreground mt-1 text-sm">
          익스텐션이 수집한 방문·체류 데이터를 실시간으로 확인합니다.
        </p>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-5 lg:gap-5">
        <section className="border-border flex min-h-[min(560px,72vh)] flex-col rounded-2xl border bg-card lg:col-span-3">
          <div className="border-border shrink-0 border-b px-4 py-3">
            <h2 className="text-sm font-semibold">실시간 활동 피드</h2>
            <p className="text-muted-foreground mt-0.5 text-xs">
              최근 {events.length}건
            </p>
          </div>
          <div className="flex min-h-0 flex-1 flex-col p-3">
            <ActivityFeedPanel
              items={events}
              loading={eventsLoading}
              error={eventsError}
            />
          </div>
        </section>

        <aside className="border-border flex min-h-[320px] flex-col rounded-2xl border bg-card lg:col-span-2">
          <div className="border-border shrink-0 border-b px-4 py-3">
            <h2 className="text-sm font-semibold">오늘의 통계</h2>
            <p className="text-muted-foreground mt-0.5 text-xs">
              KST 기준 오늘 집계
            </p>
          </div>
          <div className="flex min-h-0 flex-1 flex-col p-4">
            <TodayStatsPanel
              stats={stats}
              loading={statsLoading}
              error={statsError}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}
