import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  fetchAnalysisCompare,
  fetchMyAnalysisSnapshot,
  mapTopCategories,
  type Portrait,
} from "@/api/analyses";
import { ApiError } from "@/api/client";
import type {
  AnalysisCompareResponse,
  DbProfileResponse,
} from "@/api/types/profiler";
import { InterestPie, buildInterestLegend } from "@/components/analyses/interest-pie";
import { RadarCompareChart } from "@/components/ideals/RadarCompareChart";
import { Badge } from "@/components/ui/badge";
import { formatAnalysisDate } from "@/lib/analyses/types";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { NotFoundPage } from "@/pages/NotFoundPage";

const DELTA_CLASS = {
  positive: "text-emerald-600 dark:text-emerald-400",
  negative: "text-amber-600 dark:text-amber-400",
  neutral: "text-muted-foreground",
} as const;

/** 비교 한 축(이전/이후)의 표시 데이터 묶음 */
interface CompareSide {
  key: "from" | "to";
  badge: string;
  title: string;
  date: string;
  videos: number;
  color: string;
  portrait: Portrait | null;
  profile: DbProfileResponse | null;
}

function portraitOf(profile: DbProfileResponse | null): Portrait | null {
  if (!profile?.portrait) return null;
  return profile.portrait as unknown as Portrait;
}

function ChannelList({
  title,
  items,
}: {
  title: string;
  items: { channel: string; count: number }[];
}) {
  return (
    <div>
      <p className="text-muted-foreground mb-2 text-xs font-semibold">{title}</p>
      {items.length > 0 ? (
        <ol className="space-y-2">
          {items.slice(0, 5).map((item, i) => (
            <li key={`${item.channel}-${i}`} className="flex items-start gap-2 text-sm">
              <span className="bg-accent text-accent-foreground flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold">
                {i + 1}
              </span>
              <span className="min-w-0 flex-1 leading-snug break-words">
                {item.channel}
                <span className="text-muted-foreground ml-1 text-xs">
                  ({item.count})
                </span>
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-muted-foreground text-xs">데이터가 없습니다.</p>
      )}
    </div>
  );
}

/** 비교 축 헤더 — 색 점 + 배지 + 페르소나명 + 날짜 */
function SideHeader({ side }: { side: CompareSide }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ background: side.color }}
      />
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold">{side.title}</p>
      </div>
      <span className="text-muted-foreground ml-auto shrink-0 text-xs">
        {side.date}
        {side.videos > 0 && ` · ${side.videos}개`}
      </span>
    </div>
  );
}

/** 쇼츠 비율처럼 한 개 숫자(%)로 보는 시청 스타일 지표 */
interface StyleMetric {
  label: string;
  from: number;
  to: number;
}

/** portrait.style에 있는 순서대로 — 없으면 스킵 */
const STYLE_LABELS = ["숏폼 비율", "채널 집중도", "관심 다양성", "반복 시청"];

function styleValue(portrait: Portrait | null, label: string): number | null {
  const s = portrait?.style?.find((x) => x.label === label);
  return s ? s.value : null;
}

/** 두 스냅샷의 시청 스타일 지표를 이전/이후로 묶는다. */
function buildStyleMetrics(
  from: Portrait | null,
  to: Portrait | null,
  data: AnalysisCompareResponse,
): StyleMetric[] {
  const out: StyleMetric[] = [];
  for (const label of STYLE_LABELS) {
    const f = styleValue(from, label);
    const t = styleValue(to, label);
    if (f != null && t != null) out.push({ label, from: f, to: t });
  }
  // 탐색 깊이 — habits(0~1)을 %로 환산해 함께 표시
  out.push({
    label: "탐색 깊이",
    from: data.habits_from.exploration_depth * 100,
    to: data.habits_to.exploration_depth * 100,
  });
  return out;
}

/** 성향·관심 축 중 변화가 가장 큰 항목 */
interface Mover {
  kind: "성향" | "관심";
  label: string;
  from: number;
  to: number;
  delta: number;
  valueSuffix: string;
  deltaSuffix: string;
}

/** 성향 6축 + 관심 도메인 델타를 합쳐 변화 큰 순 상위 3개. */
function buildTopMovers(from: Portrait | null, to: Portrait | null): Mover[] {
  if (!from || !to) return [];
  const mk = (
    src: { axis: string; value: number }[],
    other: { axis: string; value: number }[],
    kind: Mover["kind"],
    valueSuffix: string,
    deltaSuffix: string,
  ): Mover[] =>
    src.map((d) => {
      const t = other.find((x) => x.axis === d.axis)?.value ?? 0;
      return {
        kind,
        label: d.axis,
        from: d.value,
        to: t,
        delta: t - d.value,
        valueSuffix,
        deltaSuffix,
      };
    });
  const all = [
    ...mk(from.disposition, to.disposition, "성향", "", "점"),
    ...mk(from.interest, to.interest, "관심", "%", "%p"),
  ];
  return all
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 3);
}

/** 시청 스타일 칩 묶음 — 각 지표를 '이전 → 이후 (+델타%p)'로. */
function MetricsStrip({ metrics }: { metrics: StyleMetric[] }) {
  if (metrics.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {metrics.map((m) => {
        const delta = Math.round(m.to - m.from);
        const tone =
          Math.abs(delta) < 1 ? "neutral" : delta > 0 ? "positive" : "negative";
        return (
          <div
            key={m.label}
            className="border-border bg-background/40 rounded-xl border px-3 py-2"
          >
            <p className="text-muted-foreground text-[11px]">{m.label}</p>
            <div className="mt-0.5 flex items-baseline gap-1.5 text-sm tabular-nums">
              <span className="text-muted-foreground">{Math.round(m.from)}%</span>
              <span className="text-muted-foreground text-xs">→</span>
              <span className="text-foreground font-semibold">
                {Math.round(m.to)}%
              </span>
              <span className={cn("text-xs font-medium", DELTA_CLASS[tone])}>
                {delta > 0 ? "+" : ""}
                {delta}%p
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function AnalysisComparePage() {
  const [params] = useSearchParams();
  const fromId = params.get("from");
  const toId = params.get("to");

  const [data, setData] = useState<AnalysisCompareResponse | null>(null);
  const [fromProfile, setFromProfile] = useState<DbProfileResponse | null>(null);
  const [toProfile, setToProfile] = useState<DbProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!fromId || !toId || fromId === toId) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      setLoading(true);
      try {
        const [compare, fromP, toP] = await Promise.all([
          fetchAnalysisCompare(fromId, toId),
          fetchMyAnalysisSnapshot(fromId).catch(() => null),
          fetchMyAnalysisSnapshot(toId).catch(() => null),
        ]);
        if (cancelled) return;
        setData(compare);
        setFromProfile(fromP);
        setToProfile(toP);
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError && (err.status === 404 || err.status === 400)) {
            setNotFound(true);
          } else {
            setNotFound(true);
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [fromId, toId]);

  const sides = useMemo<CompareSide[]>(() => {
    if (!data) return [];
    const { from_snapshot: f, to_snapshot: t } = data;
    return [
      {
        key: "from",
        badge: "기준 (이전)",
        title: f.persona_label || "이전 분석",
        date: formatAnalysisDate(f.snapshot_date),
        videos: f.total_videos,
        color: "#94a3b8",
        portrait: portraitOf(fromProfile),
        profile: fromProfile,
      },
      {
        key: "to",
        badge: "비교 (이후)",
        title: t.persona_label || "최근 분석",
        date: formatAnalysisDate(t.snapshot_date),
        videos: t.total_videos,
        color: "#0ea5e9",
        portrait: portraitOf(toProfile),
        profile: toProfile,
      },
    ];
  }, [data, fromProfile, toProfile]);

  if (notFound) {
    return <NotFoundPage />;
  }

  if (loading || !data) {
    return (
      <div className="text-muted-foreground flex h-full items-center justify-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        비교 결과 불러오는 중… (AI 요약 포함)
      </div>
    );
  }

  const { from_snapshot: fromSnap, to_snapshot: toSnap } = data;
  const fromPortrait = sides[0]?.portrait ?? null;
  const toPortrait = sides[1]?.portrait ?? null;
  const styleMetrics = buildStyleMetrics(fromPortrait, toPortrait, data);
  // 성향 6축을 이전(current)·이후(ideal)로 겹쳐 그리기용
  const dispCompare =
    fromPortrait && toPortrait
      ? fromPortrait.disposition.map((d) => ({
          label: d.axis,
          current: d.value,
          ideal:
            toPortrait.disposition.find((x) => x.axis === d.axis)?.value ?? 0,
        }))
      : [];
  const topMovers = buildTopMovers(fromPortrait, toPortrait);
  const fromInterest = fromPortrait
    ? [...fromPortrait.interest].sort((a, b) => b.value - a.value)
    : [];
  const toInterest = toPortrait
    ? [...toPortrait.interest].sort((a, b) => b.value - a.value)
    : [];
  // 두 시점 도메인 합집합(값 max)으로 공유 범례 — 색은 도메인명 고정이라 양쪽 도넛과 일치
  const interestLegend = (() => {
    const map = new Map<string, number>();
    for (const d of [...fromInterest, ...toInterest]) {
      map.set(d.axis, Math.max(map.get(d.axis) ?? 0, d.value));
    }
    return buildInterestLegend(
      [...map.entries()]
        .map(([axis, value]) => ({ axis, value }))
        .sort((a, b) => b.value - a.value),
    );
  })();

  return (
    <div className="w-full px-4 py-6 sm:px-6 sm:py-8">
      <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
        <Link to={ROUTES.ME.HOME} className="hover:text-foreground transition-colors">
          분석 목록
        </Link>
        <span>/</span>
        <span className="text-foreground">비교 분석</span>
      </nav>

      <h1 className="text-2xl font-semibold tracking-tight">비교 분석</h1>

      {/* 기준/비교 헤더 */}
      <div className="border-border mt-6 flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-4">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-sm font-semibold">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: sides[0]?.color }}
            />
            <span className="truncate">{sides[0]?.title}</span>
          </p>
          <p className="text-muted-foreground text-xs">
            {formatAnalysisDate(fromSnap.snapshot_date)}
            {fromSnap.total_videos > 0 && ` · ${fromSnap.total_videos}개 영상`}
          </p>
        </div>

        <ArrowRight className="text-muted-foreground size-5 shrink-0" />

        <div className="min-w-0 flex-1 text-right">
          <p className="flex items-center justify-end gap-1.5 text-sm font-semibold">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: sides[1]?.color }}
            />
            <span className="truncate">{sides[1]?.title}</span>
          </p>
          <p className="text-muted-foreground text-xs">
            {formatAnalysisDate(toSnap.snapshot_date)}
            {toSnap.total_videos > 0 && ` · ${toSnap.total_videos}개 영상`}
          </p>
        </div>
      </div>

      {/* AI 비교 요약 */}
      {data.narrative ? (
        <section className="border-border mt-6 rounded-2xl border bg-card p-5">
          <p className="text-muted-foreground mb-2 text-[10px] font-medium uppercase tracking-wide">
            AI 비교 요약
          </p>
          <p className="text-lg font-semibold leading-snug">{data.narrative.headline}</p>
          {topMovers.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {topMovers.map((m) => (
                <Badge
                  key={`${m.kind}-${m.label}`}
                  variant="secondary"
                  className="rounded-full"
                >
                  {m.label} {m.delta > 0 ? "▲" : "▼"}
                  {Math.abs(Math.round(m.delta))}
                  {m.deltaSuffix}
                </Badge>
              ))}
            </div>
          )}
          <div className="text-muted-foreground mt-3 space-y-1.5 text-sm leading-relaxed">
            {data.narrative.summary_text
              .split(/(?<=\.)\s+/)
              .map((s) => s.trim())
              .filter(Boolean)
              .map((sentence, i) => (
                <p key={i}>{sentence}</p>
              ))}
          </div>
          {data.narrative.key_shifts.length > 0 && (
            <ul className="mt-4 space-y-2">
              {data.narrative.key_shifts.map((item) => (
                <li key={item} className="flex gap-2 text-sm">
                  <span className="text-primary mt-1.5 size-1.5 shrink-0 rounded-full bg-current" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          )}
          {styleMetrics.length > 0 && (
            <div className="border-border mt-4 border-t pt-4">
              <p className="text-muted-foreground mb-2 text-[10px] font-medium uppercase tracking-wide">
                시청 스타일
              </p>
              <MetricsStrip metrics={styleMetrics} />
            </div>
          )}
        </section>
      ) : data.narrative_error ? (
        <div className="border-border text-muted-foreground mt-6 rounded-2xl border border-dashed px-4 py-6 text-center text-sm">
          AI 요약을 생성하지 못했습니다. 아래 비교를 참고해 주세요.
        </div>
      ) : null}

      {/* AI 요약이 없을 때만 시청 스타일 칩을 단독 카드로 (요약 안에 못 넣으므로) */}
      {!data.narrative && styleMetrics.length > 0 && (
        <section className="border-border mt-6 rounded-2xl border bg-card p-5">
          <p className="text-muted-foreground mb-2 text-[10px] font-medium uppercase tracking-wide">
            시청 스타일
          </p>
          <MetricsStrip metrics={styleMetrics} />
        </section>
      )}

      {/* 성향 스파이더(왼) + 관심 도메인(오른, 이전 → 이후 화살표) — 한 줄 */}
      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        {/* 성향 스파이더 — 이전·이후 겹쳐 보기 */}
        <div className="flex flex-col">
          <div className="border-border flex flex-1 flex-col rounded-2xl border bg-card p-5">
            <h2 className="mb-3 text-sm font-semibold">성향 스파이더</h2>
            {dispCompare.length > 0 ? (
              <>
                <div className="mb-4 flex items-center justify-center gap-6 text-xs">
                  <span className="flex min-w-0 items-center gap-1.5">
                    <span
                      className="inline-block h-2 w-2 shrink-0 rounded-full"
                      style={{ background: sides[0]?.color }}
                    />
                    <span className="text-muted-foreground truncate">
                      {sides[0]?.title}
                    </span>
                  </span>
                  <ArrowRight className="text-muted-foreground size-4 shrink-0" />
                  <span className="flex min-w-0 items-center gap-1.5">
                    <span
                      className="inline-block h-2 w-2 shrink-0 rounded-full"
                      style={{ background: sides[1]?.color }}
                    />
                    <span className="text-foreground truncate">
                      {sides[1]?.title}
                    </span>
                  </span>
                </div>
                <div className="flex flex-1 items-center justify-center">
                  <RadarCompareChart
                    axes={dispCompare}
                    size={300}
                    labelMargin={44}
                    currentColor={sides[0]?.color}
                    idealColor={sides[1]?.color}
                    dashed="current"
                  />
                </div>
              </>
            ) : (
              <p className="text-muted-foreground py-10 text-center text-sm">
                성향 데이터가 없는 분석입니다.
              </p>
            )}
          </div>
        </div>

        {/* 관심 도메인 — 한 박스, 이전 → 이후 */}
        <div className="flex flex-col">
          <div className="border-border flex flex-1 flex-col rounded-2xl border bg-card p-5">
            <h2 className="mb-3 text-sm font-semibold">관심 도메인</h2>
            <div className="flex flex-1 flex-col justify-center">
              {fromInterest.length > 0 || toInterest.length > 0 ? (
              <div className="flex items-center gap-3">
                {/* 범례 — 왼쪽 한 박스 (도메인 · 이전→이후 %) */}
                <ul className="border-border flex w-28 shrink-0 flex-col gap-1.5 rounded-xl border p-2.5">
                  {interestLegend.map((l) => (
                    <li
                      key={l.axis}
                      className="flex items-center gap-1.5 text-[11px] leading-tight"
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: l.color }}
                      />
                      <span className="whitespace-nowrap">{l.axis}</span>
                    </li>
                  ))}
                </ul>
                {/* 이전 → 이후 도넛 */}
                <div className="flex min-w-0 flex-1 items-center justify-center gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-muted-foreground mb-1 flex items-center justify-center gap-1 text-[11px]">
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: sides[0]?.color }}
                      />
                      <span className="truncate">{sides[0]?.title}</span>
                    </p>
                    <InterestPie
                      data={fromInterest}
                      size={190}
                      showLegend={false}
                      innerRadius="55%"
                      outerRadius="92%"
                    />
                  </div>
                  <ArrowRight className="text-muted-foreground size-5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-muted-foreground mb-1 flex items-center justify-center gap-1 text-[11px]">
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: sides[1]?.color }}
                      />
                      <span className="truncate">{sides[1]?.title}</span>
                    </p>
                    <InterestPie
                      data={toInterest}
                      size={190}
                      showLegend={false}
                      innerRadius="55%"
                      outerRadius="92%"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground py-10 text-center text-sm">
                관심 도메인 데이터가 없습니다.
              </p>
            )}
            </div>
          </div>
        </div>
      </section>

      {/* 상위 채널 / 카테고리 — 좌우 비교 */}
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold">상위 채널 · 카테고리</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {sides.map((s) => {
            const categories = mapTopCategories(s.profile?.top_categories ?? []);
            const longCh = s.profile?.top_channels_long ?? [];
            const shortCh = s.profile?.top_channels_short ?? [];
            const hasAny =
              categories.length > 0 || longCh.length > 0 || shortCh.length > 0;
            return (
              <div key={s.key} className="border-border rounded-2xl border bg-card p-5">
                <SideHeader side={s} />
                {hasAny ? (
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div>
                      <p className="text-muted-foreground mb-2 text-xs font-semibold">
                        상위 카테고리
                      </p>
                      {categories.length > 0 ? (
                        <ol className="space-y-2">
                          {categories.slice(0, 5).map((item, i) => (
                            <li
                              key={`${item.label}-${i}`}
                              className="flex items-start gap-2 text-sm"
                            >
                              <span className="bg-accent text-accent-foreground flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold">
                                {i + 1}
                              </span>
                              <span className="min-w-0 flex-1 leading-snug">
                                {item.label}
                                <span className="text-muted-foreground ml-1 text-xs">
                                  ({item.count})
                                </span>
                              </span>
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p className="text-muted-foreground text-xs">데이터 없음</p>
                      )}
                    </div>
                    <ChannelList title="롱폼 상위 채널" items={longCh} />
                    <ChannelList title="숏폼 상위 채널" items={shortCh} />
                  </div>
                ) : (
                  <p className="text-muted-foreground py-10 text-center text-sm">
                    채널·카테고리 데이터가 없습니다.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

    </div>
  );
}
