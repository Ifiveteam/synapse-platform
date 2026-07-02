import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCw, Target } from "lucide-react";

import { CompareBars } from "@/components/ideals/CompareBars";
import { RadarCompareChart } from "@/components/ideals/RadarCompareChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TEMPERAMENT_AXES } from "@/lib/analyses/temperament";
import { VALUES_AXES } from "@/lib/analyses/values";
import { applyIdeal, getComparison, getGuide, getIdeal } from "@/api/navigator";
import type {
  ComparisonResponse,
  GuideResponse,
  IdealResponse,
} from "@/api/types/navigator";
import { IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { ROUTES } from "@/routes";
import { useSidebarStore } from "@/stores/sidebar";

function GapBadge({ gap }: { gap: number }) {
  if (gap === 0) return <span className="text-muted-foreground text-xs">±0</span>;
  const up = gap > 0;
  return (
    <span
      className={
        up
          ? "text-primary text-xs font-medium"
          : "text-muted-foreground text-xs font-medium"
      }
    >
      {up ? "▲" : "▼"} {Math.abs(Math.round(gap))}
    </span>
  );
}

export function IdealDetailPage() {
  const { id } = useParams<{ id: string }>();
  const setActiveIdealLabel = useSidebarStore((s) => s.setActiveIdealLabel);

  const [ideal, setIdeal] = useState<IdealResponse | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [guide, setGuide] = useState<GuideResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [guideLoading, setGuideLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setNotFound(false);
    try {
      const [idealRes, cmpRes] = await Promise.all([
        getIdeal(id),
        getComparison(id),
      ]);
      setIdeal(idealRes);
      setComparison(cmpRes);
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
    // 가이드는 LLM이라 별도 로딩
    setGuideLoading(true);
    try {
      setGuide(await getGuide(id));
    } catch {
      setGuide(null);
    } finally {
      setGuideLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="text-muted-foreground mx-auto max-w-3xl px-6 py-16 text-center text-sm">
        불러오는 중…
      </div>
    );
  }

  if (notFound || !ideal || !comparison) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">
          이상향을 찾을 수 없습니다.
        </p>
        <Button asChild variant="outline" size="sm">
          <Link to={ROUTES.idealManagement}>이상향 관리로</Link>
        </Button>
      </div>
    );
  }

  const axes = comparison.gaps.map((g) => ({
    label: g.label_ko,
    current: g.current,
    ideal: g.ideal,
  }));

  const handleApply = async () => {
    await applyIdeal(ideal.id);
    setIdeal({ ...ideal, is_active: true });
    setActiveIdealLabel(ideal.persona_label || IDEAL_TYPE_LABEL[ideal.ideal_type]);
  };

  const handleRegenerateGuide = async () => {
    if (!id) return;
    setRegenerating(true);
    try {
      setGuide(await getGuide(id, true));
    } catch {
      /* 유지: 기존 가이드 그대로 둠 */
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-8">
      <Link
        to={ROUTES.idealManagement}
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex w-fit items-center gap-1.5 text-sm transition-colors"
      >
        <ArrowLeft size={16} />
        이상향 관리
      </Link>

      {/* 헤더 */}
      <div className="border-border mb-6 flex items-start gap-4 rounded-2xl border bg-card px-5 py-5">
        <div className="bg-accent text-accent-foreground flex h-12 w-12 shrink-0 items-center justify-center rounded-xl">
          <Target size={22} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-xl font-semibold tracking-tight">
              {ideal.persona_label ||
                `${IDEAL_TYPE_LABEL[ideal.ideal_type]} 이상향`}
            </h1>
            <Badge variant="outline" className="shrink-0 rounded-full">
              {IDEAL_TYPE_LABEL[ideal.ideal_type]}
            </Badge>
            {ideal.is_active ? (
              <Badge variant="indigo" className="rounded-full">
                적용 중
              </Badge>
            ) : (
              <button
                type="button"
                onClick={() => void handleApply()}
                className="border-primary text-primary hover:bg-primary/5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors"
              >
                적용
              </button>
            )}
          </div>
          {ideal.reasoning && (
            <p className="text-muted-foreground mt-1 text-sm">
              {ideal.reasoning}
            </p>
          )}
        </div>
      </div>

      {/* 현재 vs 이상향 비교 */}
      <section className="border-border mb-6 rounded-2xl border bg-card px-5 py-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">현재 vs 이상향 비교</h2>
          <span className="text-muted-foreground text-xs">
            총 차이 {Math.round(comparison.total_gap)}
          </span>
        </div>
        <div className="flex flex-col items-center">
          <RadarCompareChart axes={axes} />
          <div className="mt-2 flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="bg-muted-foreground inline-block h-2 w-4 rounded-full" />
              현재
            </span>
            <span className="flex items-center gap-1.5">
              <span className="bg-primary inline-block h-2 w-4 rounded-full" />
              이상향
            </span>
          </div>
        </div>
        <div className="border-border mt-5 flex flex-col gap-2 border-t pt-4">
          {comparison.gaps.map((g) => (
            <div
              key={g.axis}
              className="flex items-center justify-between text-xs"
            >
              <span className="font-medium">{g.label_ko}</span>
              <span className="text-muted-foreground flex items-center gap-2">
                현재 {Math.round(g.current)} → 목표 {Math.round(g.ideal)}{" "}
                <GapBadge gap={g.gap} />
              </span>
            </div>
          ))}
        </div>

        {comparison.current_vt && comparison.ideal_vt && (
          <div className="border-border mt-5 space-y-5 border-t pt-5">
            <p className="text-muted-foreground text-xs">
              가치관·기질 (막대=현재 · 목표선=이상향)
            </p>
            <CompareBars
              title="가치관"
              axes={VALUES_AXES}
              current={comparison.current_vt}
              ideal={comparison.ideal_vt}
            />
            <CompareBars
              title="기질"
              axes={TEMPERAMENT_AXES}
              current={comparison.current_vt}
              ideal={comparison.ideal_vt}
            />
          </div>
        )}
      </section>

      {/* 행동 가이드 */}
      <section className="border-border rounded-2xl border bg-card px-5 py-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-base font-semibold">이상향을 위한 행동 가이드</h2>
          {guide && !guideLoading && (
            <div className="flex shrink-0 items-center gap-2">
              {guide.generated_at && (
                <span className="text-muted-foreground text-xs">
                  {new Date(guide.generated_at).toLocaleDateString("ko-KR")} 생성
                </span>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => void handleRegenerateGuide()}
                disabled={regenerating}
                className="gap-1.5"
              >
                <RefreshCw
                  size={14}
                  className={regenerating ? "animate-spin" : ""}
                />
                다시 생성
              </Button>
            </div>
          )}
        </div>
        {guideLoading ? (
          <p className="text-muted-foreground text-sm">가이드 생성 중…</p>
        ) : !guide ? (
          <p className="text-muted-foreground text-sm">
            가이드를 불러오지 못했습니다.
          </p>
        ) : (
          <>
            {guide.stale && (
              <div className="border-border bg-secondary/50 text-muted-foreground mb-4 flex items-center gap-2 rounded-xl border px-3 py-2 text-xs">
                <RefreshCw size={14} className="shrink-0" />
                생성 이후 새 시청기록이 쌓였어요. "다시 생성"으로 최신 기록을
                반영할 수 있어요.
              </div>
            )}
            <p className="text-muted-foreground mb-4 text-sm">{guide.summary}</p>
            <ol className="flex flex-col gap-3">
              {guide.steps.map((s, i) => (
                <li key={`${s.axis}-${i}`} className="flex items-start gap-3">
                  <span className="bg-primary text-primary-foreground mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{s.title}</p>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                      {s.detail}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </>
        )}
      </section>
    </div>
  );
}
