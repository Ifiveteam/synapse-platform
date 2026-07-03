import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Target } from "lucide-react";

import { InterestPie } from "@/components/analyses/interest-pie";
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

  // 주 표시: 성향 6각 레이더(현재+이상향) · 관심 도메인 파이(현재/이상향)
  const dispRadar = comparison.disposition.map((p) => ({
    label: p.label_ko,
    current: p.current,
    ideal: p.target,
  }));
  const curPie = comparison.interest.map((p) => ({
    axis: p.domain,
    value: p.current,
  }));
  const idealPie = comparison.interest.map((p) => ({
    axis: p.domain,
    value: p.target,
  }));
  const hasTargets =
    comparison.disposition.length > 0 || comparison.interest.length > 0;

  const handleApply = async () => {
    await applyIdeal(ideal.id);
    setIdeal({ ...ideal, is_active: true });
    setActiveIdealLabel(ideal.persona_label || IDEAL_TYPE_LABEL[ideal.ideal_type]);
  };

  return (
    <div className="flex min-h-full flex-col px-4 py-5 sm:px-6 sm:py-6">
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
        {/* 주 표시: 성향 6각 레이더 + 관심 도메인 파이(현재/이상향) */}
        {hasTargets ? (
          <div className="grid gap-6 lg:grid-cols-2">
            {dispRadar.length > 0 && (
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-semibold">성향</p>
                  <div className="text-muted-foreground flex items-center gap-3 text-xs">
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
                <div className="flex justify-center">
                  <RadarCompareChart axes={dispRadar} size={260} />
                </div>
              </div>
            )}
            {curPie.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-semibold">관심 도메인</p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-muted-foreground mb-1 text-center text-xs">
                      현재
                    </p>
                    <InterestPie data={curPie} size={160} />
                  </div>
                  <div>
                    <p className="text-primary mb-1 text-center text-xs">이상향</p>
                    <InterestPie data={idealPie} size={160} />
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          // 레거시(목표 없는 옛 이상향): 8축 레이더를 그대로 노출
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
        )}

        {/* 자세히: 행동 8축 · 가치관/기질 (폴드) */}
        <details className="border-border mt-5 border-t pt-4">
          <summary className="text-muted-foreground hover:text-foreground cursor-pointer text-xs select-none">
            자세히 보기 (행동 8축 · 가치관/기질)
          </summary>
          <div className="mt-4 space-y-5">
            {hasTargets && (
              <div className="flex justify-center">
                <RadarCompareChart axes={axes} size={220} />
              </div>
            )}
            <div className="flex flex-col gap-2">
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
              <div className="space-y-5">
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
          </div>
        </details>
      </section>

      {/* 행동 가이드 */}
      <section className="border-border rounded-2xl border bg-card px-5 py-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-base font-semibold">이상향을 위한 행동 가이드</h2>
          {guide && !guideLoading && guide.generated_at && (
            <span className="text-muted-foreground shrink-0 text-xs">
              {new Date(guide.generated_at).toLocaleDateString("ko-KR")} 생성
            </span>
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
            <p className="text-muted-foreground mb-4 text-sm">{guide.summary}</p>
            <ol className="flex flex-col gap-3">
              {guide.steps.map((s, i) => (
                <li key={`${s.axis}-${i}`} className="flex items-start gap-3">
                  <span className="bg-primary text-primary-foreground mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge
                        variant={s.kind === "expand" ? "indigo" : "outline"}
                        className="rounded-full"
                      >
                        {s.kind === "expand" ? "확장" : "심화"}
                      </Badge>
                      {s.label_ko && (
                        <span className="text-muted-foreground text-xs">
                          {s.label_ko}
                        </span>
                      )}
                      <p className="text-sm font-medium">{s.title}</p>
                    </div>
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
