import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ListVideo, Target } from "lucide-react";

import {
  InterestPie,
  buildInterestLegend,
} from "@/components/analyses/interest-pie";
import { RadarCompareChart } from "@/components/ideals/RadarCompareChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { applyIdeal, getComparison, getGuide, getIdeal } from "@/api/navigator";
import type {
  ComparisonResponse,
  GuideResponse,
  IdealResponse,
} from "@/api/types/navigator";
import { IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { ROUTES } from "@/routes";
import { useSidebarStore } from "@/stores/sidebar";

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
          <Link to={ROUTES.ME.HOME}>이상향 관리로</Link>
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
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link
          to={ROUTES.ME.HOME}
          className="text-muted-foreground hover:text-foreground inline-flex w-fit items-center gap-1.5 text-sm transition-colors"
        >
          <ArrowLeft size={16} />
          이상향 관리
        </Link>
        <Button size="sm" className="gap-1.5" asChild>
          <Link to={`${ROUTES.playlists}?ideal=${ideal.id}&new=1`}>
            <ListVideo size={15} />
            재생목록 생성
          </Link>
        </Button>
      </div>

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

      {/* 현재 vs 이상향 비교 — 제목은 박스 밖, 성향/관심 도메인 별도 박스 */}
      <div className="mb-6">
        <div className="mb-3">
          <h2 className="text-base font-semibold">현재 vs 이상향 비교</h2>
        </div>
        {hasTargets ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {/* 성향 — 별도 박스 */}
            {dispRadar.length > 0 && (
              <div className="border-border flex flex-col rounded-2xl border bg-card px-5 py-5">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-semibold">성향 스파이더</p>
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
                <div className="flex flex-1 items-center justify-center">
                  <RadarCompareChart axes={dispRadar} size={280} labelMargin={40} />
                </div>
              </div>
            )}
            {/* 관심 도메인 — 별도 박스, 범례 왼쪽 */}
            {curPie.length > 0 && (
              <div className="border-border flex flex-col rounded-2xl border bg-card px-5 py-5">
                <p className="mb-2 text-sm font-semibold">관심 도메인</p>
                <div className="flex flex-1 items-center gap-3">
                  <ul className="border-border flex w-28 shrink-0 flex-col gap-1.5 rounded-xl border p-2.5">
                    {[...buildInterestLegend(curPie)]
                      .sort((a, b) => b.value - a.value)
                      .map((l) => (
                        <li
                          key={l.axis}
                          className="flex items-center gap-1.5 text-[11px] leading-tight"
                        >
                          <span
                            className="h-2 w-2 shrink-0 rounded-full"
                            style={{ background: l.color }}
                          />
                          <span className="flex-1 whitespace-nowrap">
                            {l.axis}
                          </span>
                        </li>
                      ))}
                  </ul>
                  <div className="flex min-w-0 flex-1 items-start justify-center gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-muted-foreground mb-1 text-center text-xs">
                        현재
                      </p>
                      <InterestPie
                        data={curPie}
                        size={190}
                        showLegend={false}
                        innerRadius="52%"
                        outerRadius="94%"
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-primary mb-1 text-center text-xs">
                        이상향
                      </p>
                      <InterestPie
                        data={idealPie}
                        size={190}
                        showLegend={false}
                        innerRadius="52%"
                        outerRadius="94%"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          // 레거시(목표 없는 옛 이상향): 8축 레이더를 그대로 노출
          <div className="border-border flex flex-col items-center rounded-2xl border bg-card px-5 py-5">
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
      </div>

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
