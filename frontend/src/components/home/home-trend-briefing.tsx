import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Loader2 } from "lucide-react";

import { KnowledgeGraphPanel } from "@/pages/reporter/KnowledgeGraphPanel";
import { Button } from "@/components/ui/button";
import {
  DOMAIN_HUB_GROUP,
  domainColor,
  domainLabel,
} from "@/lib/trend-domains";
import { ROUTES } from "@/routes";
import {
  fetchKnowledgeGraph,
  todayKstDateString,
  type KnowledgeGraphData,
  type KnowledgeGraphNode,
} from "@/services/reporter";

function isHub(node: KnowledgeGraphNode): boolean {
  return node.group === DOMAIN_HUB_GROUP;
}

export function HomeTrendBriefing() {
  const selectedDate = todayKstDateString();
  const [graphData, setGraphData] = useState<KnowledgeGraphData>({
    nodes: [],
    links: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKnowledgeGraph(selectedDate, 14);
      setGraphData(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "트렌드 브리핑을 불러오지 못했습니다.",
      );
      setGraphData({ nodes: [], links: [] });
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    void load();
  }, [load]);

  const topKeywords = useMemo(
    () =>
      [...graphData.nodes]
        .filter((n) => !isHub(n))
        .sort((a, b) => b.val - a.val)
        .slice(0, 5),
    [graphData.nodes],
  );

  const rangeHint =
    graphData.start_date && graphData.end_date
      ? `${graphData.start_date} — ${graphData.end_date}`
      : selectedDate;

  return (
    <div className="flex w-full flex-col pb-16 pt-10 md:pt-14">
      <header className="mx-auto mb-8 flex w-full max-w-3xl flex-col gap-3 px-6 md:mb-10 md:px-8">
        <p className="text-muted-foreground/80 text-[13px] tracking-wide">
          Synapse
        </p>
        <h1 className="text-foreground text-[2rem] leading-[1.15] font-semibold tracking-[-0.03em] md:text-[2.75rem]">
          오늘의 트렌드
        </h1>
        <p className="text-muted-foreground/70 text-[12px] tracking-wide">
          {rangeHint}
        </p>
      </header>

      {/* 지식 맵 — 전체보기와 동일한 원본 그래프 뷰 */}
      <section className="mb-12 w-full px-4 md:mb-14 md:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl">
          <KnowledgeGraphPanel
            selectedDate={selectedDate}
            externalData={graphData}
            externalLoading={loading}
            externalError={error}
            onRetry={() => void load()}
          />
        </div>
      </section>

      <section className="mx-auto mb-12 w-full max-w-3xl px-6 md:mb-14 md:px-8">
        <h2 className="text-muted-foreground mb-5 text-[12px] font-medium tracking-wide">
          Top keywords
        </h2>

        {loading && (
          <div className="text-muted-foreground flex items-center gap-2 py-6 text-[13px]">
            <Loader2 className="size-3.5 animate-spin opacity-60" />
            불러오는 중…
          </div>
        )}

        {!loading && error && (
          <div className="py-4 text-[14px]">
            <p className="text-foreground/90">불러오지 못했습니다</p>
            <p className="text-muted-foreground mt-1 text-[13px]">{error}</p>
            <button
              type="button"
              className="text-foreground mt-4 text-[13px] underline-offset-4 hover:underline"
              onClick={() => void load()}
            >
              다시 시도
            </button>
          </div>
        )}

        {!loading && !error && topKeywords.length === 0 && (
          <p className="text-muted-foreground py-6 text-[13px]">
            표시할 키워드가 없습니다
          </p>
        )}

        {!loading && !error && topKeywords.length > 0 && (
          <ol className="divide-border/60 flex flex-col divide-y">
            {topKeywords.map((node, index) => (
              <li
                key={node.id}
                className="flex items-center gap-4 py-3.5 first:pt-0 last:pb-0"
              >
                <span className="text-muted-foreground/50 w-4 shrink-0 text-[12px] tabular-nums">
                  {index + 1}
                </span>
                <span
                  className="size-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: domainColor(node.group) }}
                  title={domainLabel(node.group)}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-[15px] tracking-tight">
                    {node.id}
                  </p>
                </div>
                <span className="text-muted-foreground shrink-0 text-[12px]">
                  {domainLabel(node.group)}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <footer className="mx-auto flex w-full max-w-3xl flex-col gap-5 border-t border-border/50 px-6 pt-8 sm:flex-row sm:items-center sm:justify-between md:px-8">
        <Button
          asChild
          className="h-10 rounded-full px-5 text-[13px] font-medium shadow-none"
        >
          <Link to={ROUTES.reporterTrendGraph} className="gap-1.5">
            전체 보기
            <ArrowUpRight className="size-3.5 opacity-70" />
          </Link>
        </Button>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <Link
            to={`${ROUTES.reporterTrendGraph}?tab=report`}
            className="text-muted-foreground hover:text-foreground text-[13px] transition-colors"
          >
            리포트
          </Link>
          <Link
            to={ROUTES.reporterTrendGraph}
            className="text-muted-foreground hover:text-foreground text-[13px] transition-colors"
          >
            스트림·히트맵
          </Link>
        </div>
      </footer>
    </div>
  );
}
