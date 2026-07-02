import { ArrowUp, ArrowLeftRight, Bookmark, Loader2, Share2 } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchMyAnalyses, fetchMyAnalysisSnapshot, mapTopCategories } from "@/api/analyses";
import { ApiError } from "@/api/client";
import { fetchEmbeddingGraph, type EmbeddingGraphData } from "@/api/indexer";
import type { DbProfileResponse } from "@/api/types/profiler";
import { EmbeddingCatalogGraph } from "@/components/analyses/embedding-catalog-graph";
import { ProfileV2View } from "@/components/analyses/profile-v2-view";
import { BehaviorSpiderChart } from "@/components/analyses/behavior-spider-chart";
import { TemperamentBars } from "@/components/analyses/temperament-bars";
import { ValuesBars } from "@/components/analyses/values-bars";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatAnalysisDate } from "@/lib/analyses/types";
import { ROUTES } from "@/routes";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { Link, useParams } from "react-router-dom";

function ChannelCard({
  title,
  items,
}: {
  title: string;
  items: { channel: string; count: number }[];
}) {
  return (
    <div className="rounded-2xl border bg-card p-4">
      <p className="mb-3 text-sm font-semibold">{title}</p>
      {items.length > 0 ? (
        <ol className="space-y-2.5">
          {items.map((item, i) => (
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
        <p className="text-muted-foreground text-xs">
          해당 형식의 채널 데이터가 없습니다.
        </p>
      )}
    </div>
  );
}

export function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [profile, setProfile] = useState<DbProfileResponse | null>(null);
  const [embeddingGraph, setEmbeddingGraph] = useState<EmbeddingGraphData | null>(null);
  const [previousSnapshotId, setPreviousSnapshotId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [tab, setTab] = useState<"v1" | "v2">("v1");

  useEffect(() => {
    if (!id) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      setLoading(true);
      try {
        const data = await fetchMyAnalysisSnapshot(id);
        if (cancelled) return;

        let graph: EmbeddingGraphData | null = null;
        try {
          graph = await fetchEmbeddingGraph({ snapshotId: id });
        } catch {
          graph = null;
        }

        if (!cancelled) {
          setProfile(data);
          setEmbeddingGraph(graph);
        }

        try {
          const list = await fetchMyAnalyses();
          if (!cancelled) {
            const completed = list
              .filter((item) => item.status === "completed" && item.snapshotAt)
              .sort(
                (a, b) =>
                  new Date(a.snapshotAt!).getTime() - new Date(b.snapshotAt!).getTime(),
              );
            const index = completed.findIndex((item) => item.id === id);
            setPreviousSnapshotId(index > 0 ? completed[index - 1].id : null);
          }
        } catch {
          if (!cancelled) setPreviousSnapshotId(null);
        }
      } catch (err) {
        if (!cancelled && err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="text-muted-foreground flex h-full items-center justify-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        분석 결과 불러오는 중…
      </div>
    );
  }

  if (notFound || !profile) {
    return <NotFoundPage />;
  }

  const tags = profile.dominant_traits ?? [];
  const categories = mapTopCategories(profile.top_categories);
  const longChannels = profile.top_channels_long ?? [];
  const shortChannels = profile.top_channels_short ?? [];
  const personaTitle = profile.persona_label || "개인성향 분석 결과";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex w-full min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
        <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
          <Link to={ROUTES.home} className="hover:text-foreground transition-colors">
            홈
          </Link>
          <span>/</span>
          <Link
            to={ROUTES.myAnalyses}
            className="hover:text-foreground transition-colors"
          >
            분석결과
          </Link>
          <span>/</span>
          <span className="text-foreground">개인성향 분석 결과</span>
        </nav>

        <div className="mb-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">{personaTitle}</h1>
            <span className="text-muted-foreground text-sm">
              {formatAnalysisDate(profile.snapshot_date)}
            </span>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            {previousSnapshotId && id && (
              <Button variant="outline" size="sm" className="gap-1.5" asChild>
                <Link to={ROUTES.analysisCompare(previousSnapshotId, id)}>
                  <ArrowLeftRight size={14} />
                  이전과 비교
                </Link>
              </Button>
            )}
            <Button variant="outline" size="sm" className="gap-1.5">
              <Share2 size={14} />
              공유
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5">
              <Bookmark size={14} />
              스크랩하기
            </Button>
          </div>
        </div>

        <div className="mb-5 flex gap-4 border-b border-border">
          {(["v1", "v2"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`-mb-px border-b-2 pb-2 text-sm font-medium transition-colors ${
                tab === t
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "v1" ? "기존" : "V2 (실험)"}
            </button>
          ))}
        </div>

        {tab === "v1" ? (
        <div className="flex min-h-0 flex-1 flex-col gap-6">
          <EmbeddingCatalogGraph data={embeddingGraph} />

          <div className="flex flex-col items-stretch gap-4 lg:flex-row">
            <div className="border-border w-full shrink-0 rounded-2xl border bg-card p-5 lg:w-[400px]">
              <BehaviorSpiderChart scores={profile.scores} />
              <div className="border-border mt-5 border-t pt-5">
                <TemperamentBars scores={profile.scores} />
              </div>
            </div>

            <div className="flex min-w-0 flex-1 flex-col gap-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-2xl border bg-card p-4">
                  <p className="mb-3 text-sm font-semibold">상위 카테고리</p>
                  {categories.length > 0 ? (
                    <ol className="space-y-2.5">
                      {categories.map((item, i) => (
                        <li key={`${item.label}-${i}`} className="flex items-start gap-2 text-sm">
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
                    <p className="text-muted-foreground text-xs">
                      시청 catalog에 카테고리 데이터가 없습니다.
                    </p>
                  )}
                </div>

                <ChannelCard title="롱폼 상위 채널" items={longChannels} />
                <ChannelCard title="숏폼 상위 채널" items={shortChannels} />
              </div>

              <div className="border-border min-h-0 flex-1 rounded-2xl border bg-card p-4">
                <ValuesBars scores={profile.scores} />
              </div>
            </div>
          </div>

          <div className="border-border rounded-2xl border bg-card p-5">
            <p className="mb-3 text-sm font-semibold">요약</p>
            {profile.tone_of_user && (
              <p className="text-primary mb-2 text-sm font-semibold">
                {profile.tone_of_user}
              </p>
            )}
            <p className="text-muted-foreground text-sm leading-relaxed">
              {profile.summary_text}
            </p>
            {profile.behavior_reasoning && (
              <p className="text-muted-foreground mt-4 text-sm leading-relaxed">
                {profile.behavior_reasoning}
              </p>
            )}
            {tags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="outline"
                    className="rounded-full px-3 py-1"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        ) : (
          <ProfileV2View />
        )}
      </div>

      <div className="border-border bg-background shrink-0 border-t px-6 py-4">
        <div className="border-border flex items-center gap-3 rounded-2xl border bg-card px-4 py-3 shadow-sm">
          <input
            type="text"
            placeholder="이 분석에 대해 물어보세요..."
            className="placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none"
          />
          <Button type="button" size="icon" className="size-8 rounded-full">
            <ArrowUp size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
}
