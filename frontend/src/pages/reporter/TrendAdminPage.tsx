import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft,
  CalendarDays,
  Loader2,
  Play,
  RefreshCw,
  Sparkles,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { triggerAggregatorBatch } from "@/services/aggregator";
import {
  fetchKnowledgeGraph,
  fetchMarkdownReport,
  fetchSnapshotInventory,
  todayKstDateString,
  triggerDailyPipeline,
  type SnapshotInventory,
  type SnapshotInventoryDay,
} from "@/services/reporter";

function errorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  if (err instanceof Error && err.message.trim()) return err.message;
  return fallback;
}

export function TrendAdminPage() {
  const [selectedDate, setSelectedDate] = useState(todayKstDateString);
  const [rangeDays, setRangeDays] = useState(30);
  const [inventory, setInventory] = useState<SnapshotInventory | null>(null);
  const [loadingInventory, setLoadingInventory] = useState(true);
  const [busy, setBusy] = useState<"agg" | "reporter" | "peek" | null>(null);
  const [peek, setPeek] = useState<{
    graphNodes: number;
    graphLinks: number;
    snapshotCount: number;
    reportSource: string;
    reportPreview: string;
  } | null>(null);

  const loadInventory = useCallback(async () => {
    setLoadingInventory(true);
    try {
      const data = await fetchSnapshotInventory(selectedDate, rangeDays);
      setInventory(data);
    } catch (err) {
      toast.error(errorMessage(err, "스냅샷 목록을 불러오지 못했습니다."));
      setInventory(null);
    } finally {
      setLoadingInventory(false);
    }
  }, [selectedDate, rangeDays]);

  useEffect(() => {
    void loadInventory();
  }, [loadInventory]);

  const handleAggregator = async () => {
    if (busy) return;
    setBusy("agg");
    try {
      const result = await triggerAggregatorBatch(selectedDate);
      toast.success(result.message);
      window.setTimeout(() => void loadInventory(), 2500);
    } catch (err) {
      toast.error(errorMessage(err, "Aggregator 배치 실행에 실패했습니다."));
    } finally {
      setBusy(null);
    }
  };

  const handleReporter = async () => {
    if (busy) return;
    setBusy("reporter");
    try {
      const result = await triggerDailyPipeline(selectedDate);
      toast.success(result.message);
      window.setTimeout(() => void loadInventory(), 1500);
    } catch (err) {
      toast.error(errorMessage(err, "Reporter 파이프라인 실행에 실패했습니다."));
    } finally {
      setBusy(null);
    }
  };

  const handlePeek = async () => {
    if (busy) return;
    setBusy("peek");
    try {
      const [graph, report] = await Promise.all([
        fetchKnowledgeGraph(selectedDate, 14),
        fetchMarkdownReport(selectedDate),
      ]);
      const preview = report.markdown
        .replace(/[#>*_`]/g, "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 180);
      setPeek({
        graphNodes: graph.nodes.length,
        graphLinks: graph.links.length,
        snapshotCount: graph.snapshot_count ?? 0,
        reportSource: report.source,
        reportPreview: preview || "(비어 있음)",
      });
    } catch (err) {
      toast.error(errorMessage(err, "데이터 조회에 실패했습니다."));
      setPeek(null);
    } finally {
      setBusy(null);
    }
  };

  const daysNewestFirst = inventory
    ? [...inventory.days].sort((a, b) => b.date.localeCompare(a.date))
    : [];

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:px-6">
      <div>
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground -ml-2 mb-2 h-8 gap-1.5 px-2 text-xs"
        >
          <Link to={ROUTES.reporterTrendGraph}>
            <ArrowLeft className="size-3.5" />
            트렌드 인텔리전스로
          </Link>
        </Button>
      </div>

      <header className="flex flex-col gap-2">
        <div className="text-muted-foreground flex items-center gap-2 text-xs font-medium tracking-wider uppercase">
          <Wrench className="size-3.5" />
          Admin
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">트렌드 관리</h1>
        <p className="text-muted-foreground max-w-2xl text-sm">
          Aggregator 스냅샷 존재 여부를 확인하고, 배치·Reporter 파이프라인을
          수동 실행합니다. (권한 검사 없음)
        </p>
      </header>

      <section className="border-border bg-card rounded-2xl border p-5 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold">실행</h2>
        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="border-border flex items-center gap-2 rounded-lg border px-3 py-2">
            <CalendarDays className="text-muted-foreground size-4 shrink-0" />
            <span className="text-muted-foreground text-xs">대상일</span>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              disabled={busy !== null}
              className="bg-transparent text-sm font-medium outline-none disabled:opacity-60"
            />
          </label>

          <label className="border-border flex items-center gap-2 rounded-lg border px-3 py-2">
            <span className="text-muted-foreground text-xs">조회 일수</span>
            <select
              value={rangeDays}
              onChange={(e) => setRangeDays(Number(e.target.value))}
              disabled={busy !== null}
              className="bg-transparent text-sm font-medium outline-none disabled:opacity-60"
            >
              <option value={14}>14일</option>
              <option value={30}>30일</option>
              <option value={60}>60일</option>
            </select>
          </label>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={() => void handleAggregator()}
              disabled={busy !== null}
              className="gap-2"
            >
              {busy === "agg" ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Play className="size-4" />
              )}
              Aggregator 배치
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => void handleReporter()}
              disabled={busy !== null}
              className="gap-2"
            >
              {busy === "reporter" ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              Reporter 파이프라인
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => void handlePeek()}
              disabled={busy !== null}
              className="gap-2"
            >
              {busy === "peek" ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              데이터 확인
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => void loadInventory()}
              disabled={busy !== null || loadingInventory}
              className="gap-2"
            >
              {loadingInventory ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              목록 새로고침
            </Button>
          </div>
        </div>

        <p className="text-muted-foreground mt-3 text-xs leading-relaxed">
          권장 순서: 대상일 선택 → Aggregator 배치 → (수 초 대기) → Reporter
          파이프라인 → 홈 그래프 확인.
        </p>

        {peek && (
          <div className="border-border mt-4 rounded-xl border bg-muted/30 px-4 py-3 text-sm">
            <p className="font-medium">{selectedDate} 데이터 확인</p>
            <ul className="text-muted-foreground mt-2 space-y-1 text-xs">
              <li>
                14일 롤업 그래프 · 노드 {peek.graphNodes} · 연결 {peek.graphLinks}{" "}
                · 합산 스냅샷 {peek.snapshotCount}일
              </li>
              <li>리포트 source: {peek.reportSource}</li>
              <li className="line-clamp-2">미리보기: {peek.reportPreview}</li>
            </ul>
          </div>
        )}
      </section>

      <section className="border-border bg-card rounded-2xl border p-5 shadow-sm">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold">스냅샷 인벤토리</h2>
            <p className="text-muted-foreground mt-1 text-xs">
              {inventory
                ? `${inventory.start_date} — ${inventory.end_date} · 있음 ${inventory.present_count} · 없음 ${inventory.missing_count}`
                : "불러오는 중…"}
            </p>
          </div>
        </div>

        {loadingInventory && !inventory && (
          <div className="text-muted-foreground flex items-center gap-2 py-10 text-sm">
            <Loader2 className="size-4 animate-spin" />
            스냅샷 목록 로딩…
          </div>
        )}

        {inventory && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="text-muted-foreground border-b text-[11px] uppercase tracking-wide">
                  <th className="pb-2 pr-3 font-medium">날짜</th>
                  <th className="pb-2 pr-3 font-medium">상태</th>
                  <th className="pb-2 pr-3 font-medium">키워드</th>
                  <th className="pb-2 pr-3 font-medium">상위 키워드</th>
                  <th className="pb-2 font-medium">도메인</th>
                </tr>
              </thead>
              <tbody>
                {daysNewestFirst.map((day) => (
                  <InventoryRow
                    key={day.date}
                    day={day}
                    selected={day.date === selectedDate}
                    onSelect={() => setSelectedDate(day.date)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function InventoryRow({
  day,
  selected,
  onSelect,
}: {
  day: SnapshotInventoryDay;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr
      className={cn(
        "border-border/60 cursor-pointer border-b last:border-0",
        selected && "bg-muted/40",
      )}
      onClick={onSelect}
    >
      <td className="py-2.5 pr-3 font-medium tabular-nums">{day.date}</td>
      <td className="py-2.5 pr-3">
        {day.present ? (
          <span className="inline-flex rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] text-emerald-700 dark:text-emerald-300">
            있음
          </span>
        ) : (
          <span className="inline-flex rounded-full bg-rose-500/10 px-2 py-0.5 text-[11px] text-rose-600 dark:text-rose-300">
            없음
          </span>
        )}
      </td>
      <td className="text-muted-foreground py-2.5 pr-3 tabular-nums">
        {day.present ? day.keyword_count : "—"}
      </td>
      <td className="text-muted-foreground max-w-[240px] truncate py-2.5 pr-3 text-xs">
        {day.present ? day.top_keywords.join(", ") || "—" : "—"}
      </td>
      <td className="text-muted-foreground max-w-[200px] truncate py-2.5 text-xs">
        {day.present ? day.domain_keys.join(", ") || "—" : "—"}
      </td>
    </tr>
  );
}
