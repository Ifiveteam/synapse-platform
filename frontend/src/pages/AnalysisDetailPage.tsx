import {
  ArrowLeftRight,
  Loader2,
  Share2,
  Target,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  fetchMyAnalyses,
  fetchMyAnalysisSnapshot,
  mapTopCategories,
  type Portrait,
} from "@/api/analyses";
import { ApiError } from "@/api/client";
import { fetchEmbeddingGraph, type EmbeddingGraphData } from "@/api/indexer";
import type { DbProfileResponse, InsightExtra } from "@/api/types/profiler";
import { EmbeddingCatalogGraph } from "@/components/analyses/embedding-catalog-graph";
import { InterestPie, buildInterestLegend } from "@/components/analyses/interest-pie";
import { AxisRadar } from "@/components/analyses/axis-radar";
import { ChatMessages } from "@/components/home/chat-messages";
import { CuratorInput } from "@/components/home/curator-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatAnalysisDate } from "@/lib/analyses/types";
import { ROUTES } from "@/routes";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { getAnalysisChatStore } from "@/stores/chat";
import { useSidebarStore } from "@/stores/sidebar";
import { Link, useParams } from "react-router-dom";

/** 채팅 입력창 자체 높이(px) — 오버레이가 콘텐츠를 가리는 만큼 스크롤 여백을 확보하는 데 사용. */
const CHAT_INPUT_BAR_HEIGHT = 112;

/** 성향 스파이더 6축 설명 — 라벨 hover 시 노출. */
const DISPOSITION_DESC: Record<string, string> = {
  몰입도: "한 대상에 깊게 파고듦",
  탐험성: "여러 주제를 넓게 소비",
  팬심: "특정 인물·팀·그룹에 열광",
  트렌드민감: "유행·숏폼 즉시성",
  정보추구: "학습·전문 지향 (↔ 순수 오락)",
  감성지향: "정서·위로 추구",
};

function ChannelCard({
  title,
  items,
}: {
  title: string;
  items: { channel: string; count: number }[];
}) {
  return (
    <div className="rounded-2xl border bg-card p-4">
      <p className="mb-4 text-sm font-semibold">{title}</p>
      {items.length > 0 ? (
        <ol className="space-y-4">
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
  const [portrait, setPortrait] = useState<Portrait | null>(null);

  // 분석 id별 독립 큐레이터 세션 — 다른 분석 페이지의 대화와 섞이지 않는다.
  const useAnalysisChat = getAnalysisChatStore(id ?? "unknown");
  const messagesCount = useAnalysisChat((s) => s.messages.length);
  const hasMessages = messagesCount > 0;
  const recordAnalysisChat = useSidebarStore((s) => s.recordAnalysisChat);
  // 채팅 패널 높이(px) — 상단 핸들을 드래그해 위아래로 조절
  const [chatHeight, setChatHeight] = useState(300);
  const dragRef = useRef<{ startY: number; startH: number } | null>(null);
  // X는 대화를 지우지 않고 패널만 접는다 — 새 메시지가 오거나 다른 분석으로 이동하면 다시 펼쳐짐
  const [panelClosed, setPanelClosed] = useState(false);
  const prevMessageCountRef = useRef(messagesCount);
  const showMessagesPanel = hasMessages && !panelClosed;
  // 채팅 오버레이가 콘텐츠 하단을 가리는 높이만큼 스크롤 여백 확보
  const contentBottomPadding =
    (showMessagesPanel ? chatHeight : 0) + CHAT_INPUT_BAR_HEIGHT;

  useEffect(() => {
    setPanelClosed(false);
  }, [id]);

  useEffect(() => {
    if (messagesCount > prevMessageCountRef.current) {
      setPanelClosed(false);
    }
    prevMessageCountRef.current = messagesCount;
  }, [messagesCount]);

  // 이 분석에서 대화가 시작되면 사이드바 '채팅 기록'에 기록.
  // profile.snapshot_id === id로 확인 — id는 바로 바뀌지만 profile은 비동기로 늦게
  // 갱신되므로, 이 확인 없이는 다른 분석으로 이동하는 찰나에 이전 분석의 제목이
  // 새 id에 잘못 기록되는 경쟁 상태가 생긴다.
  useEffect(() => {
    if (id && hasMessages && profile?.snapshot_id === id) {
      recordAnalysisChat(id, portrait?.persona_label || "개인성향 분석 결과");
    }
  }, [id, hasMessages, portrait, profile, recordAnalysisChat]);

  // 상단 핸들 드래그 → 채팅 패널 높이 조절 (위로 끌면 커지고 아래로 끌면 작아짐)
  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startY: e.clientY, startH: chatHeight };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = dragRef.current.startY - ev.clientY;
      const next = Math.min(
        Math.max(dragRef.current.startH + delta, 140),
        window.innerHeight * 0.7,
      );
      setChatHeight(next);
    };
    const onUp = () => {
      dragRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

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
          // 업로드 시 저장된 portrait가 스냅샷에 함께 옴 → 바로 사용
          if (data.portrait)
            setPortrait(data.portrait as unknown as Portrait);
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
  const insight =
    ((profile.supporting_evidence as { insight?: InsightExtra } | null)
      ?.insight ?? {}) as InsightExtra;
  const categories = mapTopCategories(profile.top_categories);
  const longChannels = profile.top_channels_long ?? [];
  const shortChannels = profile.top_channels_short ?? [];
  const personaTitle = portrait?.persona_label || "개인성향 분석 결과";
  // 도넛·범례 공통: 값 내림차순 정렬 (색상 인덱스 일치를 위해 같은 배열 사용)
  const sortedInterest = portrait
    ? [...portrait.interest].sort((a, b) => b.value - a.value)
    : [];

  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <div className="flex w-full min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
        <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
          <Link to={ROUTES.home} className="hover:text-foreground transition-colors">
            홈
          </Link>
          <span>/</span>
          <Link
            to={ROUTES.ME.HOME}
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
            {id && (
              <Button size="sm" className="gap-1.5" asChild>
                <Link to={`${ROUTES.idealSetup}?select=${id}`}>
                  <Target size={14} />
                  이상향 분석
                </Link>
              </Button>
            )}
          </div>
        </div>

        {portrait && portrait.keywords.length > 0 && (
          <div className="mb-6 -mt-2 flex flex-wrap gap-2">
            {portrait.keywords.map((k) => (
              <Badge
                key={k}
                variant="secondary"
                className="rounded-full px-3 py-1 text-sm"
              >
                #{k}
              </Badge>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-6">
          {portrait && (
            <div className="border-border rounded-2xl border bg-card p-5">
              {portrait.reasoning && (
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {portrait.reasoning}
                </p>
              )}
            </div>
          )}

          <EmbeddingCatalogGraph data={embeddingGraph} hideControls={showMessagesPanel} />

          <div className="flex flex-col gap-4 lg:flex-row">
            {portrait && (
              <div className="border-border rounded-2xl border bg-card p-5 lg:w-[480px] lg:shrink-0">
                <div className="mb-1 flex items-baseline justify-between">
                  <p className="text-sm font-semibold">성향 스파이더</p>
                  <span className="text-muted-foreground text-[10px]">
                    0~100 · 라벨에 커서를 올리면 설명
                  </span>
                </div>
                <AxisRadar
                  data={portrait.disposition}
                  color="#0ea5e9"
                  axisDescriptions={DISPOSITION_DESC}
                  compact
                />
                <div className="border-border mt-5 border-t pt-5">
                  <p className="mb-3 text-sm font-semibold">소비 스타일</p>
                  <div className="space-y-2.5">
                    {portrait.style.map((s) => (
                      <div key={s.label}>
                        <div className="mb-1 flex justify-between text-xs">
                          <span>{s.label}</span>
                          <span className="text-muted-foreground tabular-nums">
                            {s.value}
                          </span>
                        </div>
                        <div className="bg-muted h-2 rounded-full">
                          <div
                            className="bg-primary h-2 rounded-full"
                            style={{ width: `${Math.min(100, s.value)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div className="border-border min-w-0 flex-1 rounded-2xl border bg-card p-5">
              <p className="mb-3 text-sm font-semibold">요약</p>
              {tags.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-2">
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
              {profile.tone_of_user && (
                <p className="text-primary mb-3 text-sm font-semibold">
                  {profile.tone_of_user}
                </p>
              )}
              <p className="text-muted-foreground text-sm leading-relaxed">
                {profile.summary_text}
              </p>

              {(insight.strengths || insight.weaknesses) && (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {insight.strengths && (
                    <div className="border-border bg-muted/30 rounded-xl border p-3">
                      <p className="mb-1 text-xs font-semibold text-emerald-500">
                        강점
                      </p>
                      <p className="text-muted-foreground text-xs leading-relaxed">
                        {insight.strengths}
                      </p>
                    </div>
                  )}
                  {insight.weaknesses && (
                    <div className="border-border bg-muted/30 rounded-xl border p-3">
                      <p className="mb-1 text-xs font-semibold text-amber-500">
                        맹점
                      </p>
                      <p className="text-muted-foreground text-xs leading-relaxed">
                        {insight.weaknesses}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {insight.content_preferences &&
                insight.content_preferences.length > 0 && (
                  <div className="mt-4">
                    <p className="text-muted-foreground mb-2 text-xs font-semibold">
                      선호 콘텐츠 유형
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {insight.content_preferences.map((p, i) => (
                        <Badge
                          key={`${p}-${i}`}
                          variant="secondary"
                          className="rounded-full px-3 py-1 text-xs font-normal"
                        >
                          {p}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </div>

          {portrait && (
            <div className="flex flex-col gap-4 lg:flex-row">
              <div className="border-border rounded-2xl border bg-card p-5 lg:w-[480px] lg:shrink-0">
                <p className="mb-3 text-sm font-semibold">관심사</p>
                <div className="flex items-start gap-3">
                  <ul className="border-border flex w-36 shrink-0 flex-col gap-1.5 rounded-xl border p-2.5">
                    {buildInterestLegend(sortedInterest).map((l) => (
                      <li
                        key={l.axis}
                        className="flex items-center gap-1.5 text-[11px] leading-tight"
                      >
                        <span
                          className="h-2 w-2 shrink-0 rounded-full"
                          style={{ background: l.color }}
                        />
                        <span className="flex-1 whitespace-nowrap">{l.axis}</span>
                        <span className="text-muted-foreground shrink-0 tabular-nums">
                          {l.pct}%
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div className="-mt-3 -mr-1 min-w-0 flex-1">
                    <InterestPie
                      data={sortedInterest}
                      size={230}
                      showLegend={false}
                      innerRadius="58%"
                      outerRadius="92%"
                    />
                  </div>
                </div>
              </div>

              <div className="grid min-w-0 flex-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-2xl border bg-card p-4">
                  <p className="mb-4 text-sm font-semibold">상위 카테고리</p>
                  {categories.length > 0 ? (
                    <ol className="space-y-4">
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
            </div>
          )}

        </div>

        {/* 채팅 오버레이에 가려지는 만큼 스크롤 여백 확보 (flex 컨테이너 자체의 padding-bottom은
            스크롤 영역에서 무시되는 경우가 있어 별도 spacer로 처리) */}
        <div
          style={{ height: contentBottomPadding }}
          className="shrink-0"
          aria-hidden="true"
        />
      </div>

      {/* 채팅 오버레이 — 분석 콘텐츠 위에 떠서 뒤가 블러 처리되어 비침 */}
      <div className="border-border bg-card/70 backdrop-blur-lg absolute inset-x-0 bottom-0 z-10 flex flex-col border-t">
        {showMessagesPanel && (
          <div className="flex shrink-0 flex-col" style={{ height: chatHeight }}>
            {/* 상단 드래그 핸들 — 위아래로 끌어 높이 조절 */}
            <div
              onMouseDown={startResize}
              role="separator"
              aria-orientation="horizontal"
              title="드래그해서 채팅 크기 조절"
              className="group flex h-3 shrink-0 cursor-ns-resize items-center justify-center"
            >
              <div className="bg-border group-hover:bg-muted-foreground/60 h-1 w-10 rounded-full transition-colors" />
            </div>

            <div className="flex shrink-0 items-center justify-between px-6 pb-1">
              <span className="text-muted-foreground text-xs font-semibold">
                이 분석에 대한 대화
              </span>
              <button
                type="button"
                onClick={() => setPanelClosed(true)}
                aria-label="대화 패널 접기"
                className="text-muted-foreground hover:text-foreground rounded-full p-1 transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <ChatMessages useStore={useAnalysisChat} maxWidthClassName="max-w-3xl" />
          </div>
        )}

        <CuratorInput
          useStore={useAnalysisChat}
          maxWidthClassName="max-w-3xl"
          placeholder="분석에 대해 무엇이든 물어보세요..."
          analysisId={id}
        />
      </div>
    </div>
  );
}
