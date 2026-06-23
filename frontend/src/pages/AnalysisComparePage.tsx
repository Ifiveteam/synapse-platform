import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeftRight, Loader2, Minus, Plus, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchAnalysisCompare } from "@/api/analyses";
import { ApiError } from "@/api/client";
import type { AnalysisCompareResponse } from "@/api/types/profiler";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatHabitDelta,
  formatHabitPercent,
  HABIT_METRICS,
  type HabitMetricKey,
} from "@/lib/analyses/habit-metrics";
import {
  ALL_SCORE_AXES,
  SCORE_GROUP_LABELS,
  scoreAxisLabel,
} from "@/lib/analyses/score-labels";
import { formatAnalysisDate } from "@/lib/analyses/types";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { NotFoundPage } from "@/pages/NotFoundPage";

function formatScoreDelta(delta: number): string {
  const rounded = Math.round(delta * 10) / 10;
  if (rounded === 0) return "0";
  return `${rounded > 0 ? "+" : ""}${rounded}`;
}

function deltaTone(
  delta: number,
  higherIsBetter: boolean,
): "positive" | "negative" | "neutral" {
  if (Math.abs(delta) < 0.005) return "neutral";
  const improved = higherIsBetter ? delta > 0 : delta < 0;
  return improved ? "positive" : "negative";
}

const DELTA_CLASS = {
  positive: "text-emerald-600 dark:text-emerald-400",
  negative: "text-amber-600 dark:text-amber-400",
  neutral: "text-muted-foreground",
} as const;

function HabitRow({
  label,
  hint,
  from,
  to,
  delta,
  higherIsBetter,
}: {
  label: string;
  hint: string;
  from: number;
  to: number;
  delta: number;
  higherIsBetter: boolean;
}) {
  const tone = deltaTone(delta, higherIsBetter);

  return (
    <div className="border-border border-b py-3 last:border-b-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">{label}</p>
          <p className="text-muted-foreground text-xs">{hint}</p>
        </div>
        <span className={cn("shrink-0 text-sm font-semibold tabular-nums", DELTA_CLASS[tone])}>
          {formatHabitDelta(delta)}
        </span>
      </div>
      <div className="text-muted-foreground mt-2 flex items-center gap-2 text-xs tabular-nums">
        <span>{formatHabitPercent(from)}</span>
        <ArrowLeftRight className="size-3 shrink-0" />
        <span className="text-foreground font-medium">{formatHabitPercent(to)}</span>
      </div>
    </div>
  );
}

function ScoreDeltaRow({ label, from, to, delta }: { label: string; from: number; to: number; delta: number }) {
  const tone = deltaTone(delta, true);

  return (
    <div className="flex items-center gap-3 py-2">
      <span className="min-w-0 flex-1 truncate text-sm">{label}</span>
      <span className="text-muted-foreground w-10 shrink-0 text-right text-xs tabular-nums">
        {Math.round(from)}
      </span>
      <span className={cn("w-12 shrink-0 text-right text-sm font-semibold tabular-nums", DELTA_CLASS[tone])}>
        {formatScoreDelta(delta)}
      </span>
      <span className="text-foreground w-10 shrink-0 text-right text-xs font-medium tabular-nums">
        {Math.round(to)}
      </span>
    </div>
  );
}

function ChangeList({
  title,
  added,
  removed,
  emptyMessage,
}: {
  title: string;
  added: string[];
  removed: string[];
  emptyMessage: string;
}) {
  if (added.length === 0 && removed.length === 0) {
    return (
      <div className="border-border rounded-2xl border bg-card p-4">
        <p className="mb-2 text-sm font-semibold">{title}</p>
        <p className="text-muted-foreground text-xs">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="border-border rounded-2xl border bg-card p-4">
      <p className="mb-3 text-sm font-semibold">{title}</p>
      <div className="space-y-3">
        {added.length > 0 && (
          <div>
            <p className="text-muted-foreground mb-1.5 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide">
              <Plus className="size-3" />
              새로 등장
            </p>
            <div className="flex flex-wrap gap-1.5">
              {added.map((item) => (
                <Badge key={`add-${item}`} variant="secondary" className="rounded-full">
                  {item}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {removed.length > 0 && (
          <div>
            <p className="text-muted-foreground mb-1.5 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide">
              <Minus className="size-3" />
              사라짐
            </p>
            <div className="flex flex-wrap gap-1.5">
              {removed.map((item) => (
                <Badge key={`rm-${item}`} variant="outline" className="rounded-full">
                  {item}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function AnalysisComparePage() {
  const [params] = useSearchParams();
  const fromId = params.get("from");
  const toId = params.get("to");

  const [data, setData] = useState<AnalysisCompareResponse | null>(null);
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
        const result = await fetchAnalysisCompare(fromId, toId);
        if (!cancelled) setData(result);
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

  const topScoreChanges = useMemo(() => {
    if (!data) return [];
    return ALL_SCORE_AXES.map(({ key, group }) => ({
      key,
      group,
      label: scoreAxisLabel(key),
      from: data.from_snapshot.scores[key] ?? 0,
      to: data.to_snapshot.scores[key] ?? 0,
      delta: data.scores_delta[key] ?? 0,
    }))
      .filter((item) => Math.abs(item.delta) >= 0.5)
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
      .slice(0, 10);
  }, [data]);

  const groupedScoreChanges = useMemo(() => {
    const groups: Record<string, typeof topScoreChanges> = {
      values: [],
      temperament: [],
      behavior: [],
    };
    for (const item of topScoreChanges) {
      groups[item.group].push(item);
    }
    return groups;
  }, [topScoreChanges]);

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
  const fromTitle = fromSnap.persona_label || "이전 분석";
  const toTitle = toSnap.persona_label || "최근 분석";
  const personaChanged = fromTitle !== toTitle;
  const shortsDeltaPct = Math.round(data.shorts_ratio_delta * 100);

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-8 pb-12">
      <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
        <Link to={ROUTES.myAnalyses} className="hover:text-foreground transition-colors">
          분석 목록
        </Link>
        <span>/</span>
        <span className="text-foreground">비교 분석</span>
      </nav>

      <h1 className="text-2xl font-semibold tracking-tight">비교 분석</h1>
      <p className="text-muted-foreground mt-1 text-sm">
        두 시점의 성향·시청 패턴 변화를 비교합니다.
      </p>

      <div className="border-border mt-6 flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-4">
        <div className="min-w-0 flex-1">
          <p className="text-muted-foreground text-[10px] font-medium uppercase tracking-wide">
            기준 (이전)
          </p>
          <p className="truncate text-sm font-semibold">{fromTitle}</p>
          <p className="text-muted-foreground text-xs">
            {formatAnalysisDate(fromSnap.snapshot_date)}
            {fromSnap.total_videos > 0 && ` · ${fromSnap.total_videos}개 영상`}
          </p>
        </div>

        <ArrowLeftRight className="text-muted-foreground size-5 shrink-0" />

        <div className="min-w-0 flex-1 text-right">
          <p className="text-muted-foreground text-[10px] font-medium uppercase tracking-wide">
            비교 (이후)
          </p>
          <p className="truncate text-sm font-semibold">{toTitle}</p>
          <p className="text-muted-foreground text-xs">
            {formatAnalysisDate(toSnap.snapshot_date)}
            {toSnap.total_videos > 0 && ` · ${toSnap.total_videos}개 영상`}
          </p>
        </div>
      </div>

      {personaChanged && !data.narrative && (
        <div className="border-primary/20 bg-primary/5 mt-4 rounded-2xl border p-4">
          <p className="text-sm font-semibold">페르소나 변화</p>
          <p className="text-muted-foreground mt-1 text-sm">
            <span className="text-foreground">{fromTitle}</span>
            {" → "}
            <span className="text-foreground font-medium">{toTitle}</span>
          </p>
        </div>
      )}

      {data.narrative ? (
        <section className="border-border mt-6 rounded-2xl border bg-card p-5">
          <p className="text-muted-foreground mb-2 text-[10px] font-medium uppercase tracking-wide">
            AI 비교 요약
          </p>
          <p className="text-lg font-semibold leading-snug">{data.narrative.headline}</p>
          <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
            {data.narrative.summary_text}
          </p>
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
          {data.narrative.stable_traits.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {data.narrative.stable_traits.map((trait) => (
                <Badge key={trait} variant="secondary" className="rounded-full">
                  {trait}
                </Badge>
              ))}
            </div>
          )}
          {data.narrative.viewing_pattern_note && (
            <p className="text-muted-foreground border-border mt-4 border-t pt-4 text-sm leading-relaxed">
              {data.narrative.viewing_pattern_note}
            </p>
          )}
        </section>
      ) : data.narrative_error ? (
        <div className="border-border text-muted-foreground mt-6 rounded-2xl border border-dashed px-4 py-6 text-center text-sm">
          AI 요약을 생성하지 못했습니다. 아래 수치 비교를 참고해 주세요.
        </div>
      ) : null}

      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold">시청 습관 지표</h2>
        <div className="border-border rounded-2xl border bg-card px-4">
          {HABIT_METRICS.map(({ key, label, hint, higherIsBetter }) => (
            <HabitRow
              key={key}
              label={label}
              hint={hint}
              from={data.habits_from[key as HabitMetricKey]}
              to={data.habits_to[key as HabitMetricKey]}
              delta={data.habits_delta[key as HabitMetricKey]}
              higherIsBetter={higherIsBetter}
            />
          ))}
        </div>
        {Math.abs(data.shorts_ratio_delta) >= 0.01 && (
          <p className="text-muted-foreground mt-2 text-xs">
            쇼츠 비율{" "}
            <span className={cn("font-medium", DELTA_CLASS[deltaTone(data.shorts_ratio_delta, false)])}>
              {shortsDeltaPct > 0 ? "+" : ""}
              {shortsDeltaPct}%p
            </span>
            {" "}
            ({formatHabitPercent(fromSnap.shorts_ratio)} → {formatHabitPercent(toSnap.shorts_ratio)})
          </p>
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold">성향 점수 변화</h2>
        {topScoreChanges.length === 0 ? (
          <div className="border-border text-muted-foreground rounded-2xl border border-dashed px-4 py-8 text-center text-sm">
            두 스냅샷 간 유의미한 점수 변화가 없습니다.
          </div>
        ) : (
          <div className="space-y-4">
            {(["values", "temperament", "behavior"] as const).map((group) => {
              const items = groupedScoreChanges[group];
              if (items.length === 0) return null;
              return (
                <div key={group} className="border-border rounded-2xl border bg-card p-4">
                  <p className="text-muted-foreground mb-2 text-[10px] font-medium uppercase tracking-wide">
                    {SCORE_GROUP_LABELS[group]}
                  </p>
                  <div className="text-muted-foreground mb-1 flex items-center gap-3 text-[10px]">
                    <span className="flex-1" />
                    <span className="w-10 shrink-0 text-right">이전</span>
                    <span className="w-12 shrink-0 text-right">변화</span>
                    <span className="w-10 shrink-0 text-right">이후</span>
                  </div>
                  {items.map((item) => (
                    <ScoreDeltaRow
                      key={item.key}
                      label={item.label}
                      from={item.from}
                      to={item.to}
                      delta={item.delta}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <ChangeList
          title="특성 태그"
          added={data.traits_added}
          removed={data.traits_removed}
          emptyMessage="두 분석의 특성 태그가 동일합니다."
        />
        <ChangeList
          title="상위 채널"
          added={data.channels_added}
          removed={data.channels_removed}
          emptyMessage="상위 채널 구성이 같습니다."
        />
      </div>

      {!data.narrative && (toSnap.summary_text || fromSnap.summary_text) && (
        <section className="border-border mt-6 rounded-2xl border bg-card p-5">
          <p className="mb-3 text-sm font-semibold">요약 비교</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-muted-foreground mb-1 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide">
                <TrendingDown className="size-3" />
                이전
              </p>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {fromSnap.summary_text || "—"}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground mb-1 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide">
                <TrendingUp className="size-3" />
                이후
              </p>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {toSnap.summary_text || "—"}
              </p>
            </div>
          </div>
        </section>
      )}

      <div className="mt-8 flex flex-wrap gap-2">
        <Button variant="outline" size="sm" asChild>
          <Link to={ROUTES.myAnalyses}>목록으로</Link>
        </Button>
        <Button variant="ghost" size="sm" asChild>
          <Link to={ROUTES.analysisDetail(fromSnap.snapshot_id)}>이전 분석 보기</Link>
        </Button>
        <Button variant="ghost" size="sm" asChild>
          <Link to={ROUTES.analysisDetail(toSnap.snapshot_id)}>최근 분석 보기</Link>
        </Button>
      </div>
    </div>
  );
}
