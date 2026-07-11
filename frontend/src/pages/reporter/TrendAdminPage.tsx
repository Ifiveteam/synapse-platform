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
import { domainLabel } from "@/lib/trend-domains";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { triggerAggregatorBatch } from "@/services/aggregator";
import {
  fetchSnapshotDetail,
  fetchSnapshotInventory,
  todayKstDateString,
  triggerDailyPipeline,
  type SnapshotDetail,
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

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      timeZone: "Asia/Seoul",
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function TrendAdminPage() {
  const inventoryEndDate = todayKstDateString();
  const [selectedDate, setSelectedDate] = useState(inventoryEndDate);
  const [rangeDays, setRangeDays] = useState(30);
  const [inventory, setInventory] = useState<SnapshotInventory | null>(null);
  const [loadingInventory, setLoadingInventory] = useState(true);
  const [detail, setDetail] = useState<SnapshotDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [busy, setBusy] = useState<"agg" | "reporter" | null>(null);

  const loadInventory = useCallback(async () => {
    setLoadingInventory(true);
    try {
      const data = await fetchSnapshotInventory(inventoryEndDate, rangeDays);
      setInventory(data);
    } catch (err) {
      toast.error(errorMessage(err, "스냅샷 목록을 불러오지 못했습니다."));
      setInventory(null);
    } finally {
      setLoadingInventory(false);
    }
  }, [inventoryEndDate, rangeDays]);

  const loadDetail = useCallback(async (date: string) => {
    setLoadingDetail(true);
    try {
      const data = await fetchSnapshotDetail(date);
      setDetail(data);
    } catch (err) {
      toast.error(errorMessage(err, "날짜 상세를 불러오지 못했습니다."));
      setDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    void loadInventory();
  }, [loadInventory]);

  useEffect(() => {
    void loadDetail(selectedDate);
  }, [selectedDate, loadDetail]);

  const handleAggregator = async () => {
    if (busy) return;
    setBusy("agg");
    try {
      const result = await triggerAggregatorBatch(selectedDate);
      toast.success(result.message);
      window.setTimeout(() => {
        void loadInventory();
        void loadDetail(selectedDate);
      }, 2500);
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
      window.setTimeout(() => {
        void loadInventory();
        void loadDetail(selectedDate);
      }, 1500);
    } catch (err) {
      toast.error(errorMessage(err, "Reporter 파이프라인 실행에 실패했습니다."));
    } finally {
      setBusy(null);
    }
  };

  const daysNewestFirst = inventory
    ? [...inventory.days].sort((a, b) => b.date.localeCompare(a.date))
    : [];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 md:px-6">
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
          날짜별 스냅샷을 자세히 확인하고 Aggregator·Reporter를 수동 실행합니다.
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
            <span className="text-muted-foreground text-xs">목록 일수</span>
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
              variant="ghost"
              onClick={() => {
                void loadInventory();
                void loadDetail(selectedDate);
              }}
              disabled={busy !== null || loadingInventory || loadingDetail}
              className="gap-2"
            >
              {loadingInventory || loadingDetail ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              새로고침
            </Button>
          </div>
        </div>
        <p className="text-muted-foreground mt-3 text-xs leading-relaxed">
          권장 순서: 날짜 선택 → Aggregator 배치 → (수 초 대기) → Reporter
          파이프라인.
        </p>
      </section>

      <section className="border-border bg-card rounded-2xl border p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold">{selectedDate} 상세</h2>
            <p className="text-muted-foreground mt-1 text-xs">
              행을 클릭하거나 대상일을 바꾸면 이 패널이 갱신됩니다.
            </p>
          </div>
          {loadingDetail && (
            <Loader2 className="text-muted-foreground size-4 animate-spin" />
          )}
        </div>

        {!loadingDetail && !detail && (
          <p className="text-muted-foreground text-sm">상세 데이터가 없습니다.</p>
        )}

        {detail && !detail.present && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-4 text-sm">
            <p className="font-medium text-rose-700 dark:text-rose-300">
              이 날짜의 global_trends_snapshot이 없습니다
            </p>
            <p className="text-muted-foreground mt-1 text-xs">
              Aggregator 배치를 실행하면 스냅샷이 생성됩니다. 리포트 source:{" "}
              {detail.report_source ?? "—"}
            </p>
          </div>
        )}

        {detail?.present && (
          <div className="flex flex-col gap-6">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MetaCard label="스냅샷 ID" value={detail.snapshot_id ?? "—"} mono />
              <MetaCard
                label="snapshot_date"
                value={formatDateTime(detail.snapshot_date)}
              />
              <MetaCard
                label="created_at"
                value={formatDateTime(detail.created_at)}
              />
              <MetaCard
                label="당일 그래프"
                value={`${detail.day_graph_nodes ?? 0} nodes · ${detail.day_graph_links ?? 0} links`}
              />
              <MetaCard
                label="리포트"
                value={detail.report_source ?? "—"}
              />
              <MetaCard
                label="semantic links"
                value={String(detail.semantic_link_count)}
              />
              <MetaCard
                label="context map"
                value={`${detail.context_count} contexts`}
              />
              <MetaCard
                label="cross-domain insights"
                value={detail.has_cross_domain_insights ? "있음" : "없음"}
              />
            </div>

            {detail.report_preview && (
              <div>
                <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  리포트 미리보기
                </h3>
                <p className="text-muted-foreground rounded-lg bg-muted/40 px-3 py-2 text-xs leading-relaxed">
                  {detail.report_preview}
                </p>
              </div>
            )}

            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  도메인 ({detail.domains.length})
                </h3>
                <div className="overflow-x-auto rounded-xl border">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-muted-foreground border-b bg-muted/30">
                        <th className="px-3 py-2 font-medium">도메인</th>
                        <th className="px-3 py-2 font-medium">users</th>
                        <th className="px-3 py-2 font-medium">duration</th>
                        <th className="px-3 py-2 font-medium">weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.domains.map((row) => (
                        <tr key={row.domain} className="border-b last:border-0">
                          <td className="px-3 py-2">{domainLabel(row.domain)}</td>
                          <td className="px-3 py-2 tabular-nums">{row.user_count}</td>
                          <td className="px-3 py-2 tabular-nums">
                            {row.total_duration}
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {row.avg_weight.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                      {detail.domains.length === 0 && (
                        <tr>
                          <td
                            colSpan={4}
                            className="text-muted-foreground px-3 py-4 text-center"
                          >
                            도메인 데이터 없음
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  8축 평균
                </h3>
                <div className="overflow-x-auto rounded-xl border">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-muted-foreground border-b bg-muted/30">
                        <th className="px-3 py-2 font-medium">축</th>
                        <th className="px-3 py-2 font-medium">값</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(detail.axes).map(([axis, value]) => (
                        <tr key={axis} className="border-b last:border-0">
                          <td className="px-3 py-2">{axis}</td>
                          <td className="px-3 py-2 tabular-nums">
                            {value.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                      {Object.keys(detail.axes).length === 0 && (
                        <tr>
                          <td
                            colSpan={2}
                            className="text-muted-foreground px-3 py-4 text-center"
                          >
                            8축 데이터 없음
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                급상승 키워드 ({detail.keywords.length})
              </h3>
              <div className="max-h-72 overflow-auto rounded-xl border">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-card">
                    <tr className="text-muted-foreground border-b bg-muted/30">
                      <th className="px-3 py-2 font-medium">#</th>
                      <th className="px-3 py-2 font-medium">키워드</th>
                      <th className="px-3 py-2 font-medium">score</th>
                      <th className="px-3 py-2 font-medium">count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.keywords.map((row) => (
                      <tr key={`${row.rank}-${row.keyword}`} className="border-b last:border-0">
                        <td className="text-muted-foreground px-3 py-2 tabular-nums">
                          {row.rank || "—"}
                        </td>
                        <td className="px-3 py-2 font-medium">{row.keyword}</td>
                        <td className="px-3 py-2 tabular-nums">
                          {row.score.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 tabular-nums">{row.count_today}</td>
                      </tr>
                    ))}
                    {detail.keywords.length === 0 && (
                      <tr>
                        <td
                          colSpan={4}
                          className="text-muted-foreground px-3 py-4 text-center"
                        >
                          키워드 없음
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  Semantic links (상위 {detail.semantic_links.length})
                </h3>
                <div className="max-h-56 overflow-auto rounded-xl border">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-card">
                      <tr className="text-muted-foreground border-b bg-muted/30">
                        <th className="px-3 py-2 font-medium">source</th>
                        <th className="px-3 py-2 font-medium">target</th>
                        <th className="px-3 py-2 font-medium">sim</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.semantic_links.map((link) => (
                        <tr
                          key={`${link.source}-${link.target}`}
                          className="border-b last:border-0"
                        >
                          <td className="px-3 py-2">{link.source}</td>
                          <td className="px-3 py-2">{link.target}</td>
                          <td className="px-3 py-2 tabular-nums">
                            {link.similarity.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                      {detail.semantic_links.length === 0 && (
                        <tr>
                          <td
                            colSpan={3}
                            className="text-muted-foreground px-3 py-4 text-center"
                          >
                            링크 없음
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex flex-col gap-4">
                <div>
                  <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    외부 시장 키워드
                  </h3>
                  <p className="text-muted-foreground text-xs leading-relaxed">
                    {detail.external_keywords.length > 0
                      ? detail.external_keywords.join(" · ")
                      : "없음"}
                  </p>
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    스크랩 카테고리
                  </h3>
                  <p className="text-muted-foreground text-xs leading-relaxed">
                    {detail.scrap_categories.length > 0
                      ? detail.scrap_categories.join(" · ")
                      : "없음"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="border-border bg-card rounded-2xl border p-5 shadow-sm">
        <div className="mb-4">
          <h2 className="text-sm font-semibold">스냅샷 인벤토리</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            {inventory
              ? `${inventory.start_date} — ${inventory.end_date} · 있음 ${inventory.present_count} · 없음 ${inventory.missing_count}`
              : "불러오는 중…"}
          </p>
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

function MetaCard({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-xl border bg-muted/20 px-3 py-2.5">
      <p className="text-muted-foreground text-[10px] tracking-wide uppercase">
        {label}
      </p>
      <p
        className={cn(
          "mt-1 truncate text-xs font-medium",
          mono && "font-mono text-[11px]",
        )}
        title={value}
      >
        {value}
      </p>
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
