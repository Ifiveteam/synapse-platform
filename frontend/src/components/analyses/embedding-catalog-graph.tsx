import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RotateCcw } from "lucide-react";

import type { EmbeddingGraphData } from "@/api/indexer";
import { constellationCategoryColorMap } from "@/lib/analyses/category-colors";
import {
  neighborIdSet,
  sortedNeighborsBySimilarity,
  toCatalogForceGraph,
  type CatalogForceLink,
  type CatalogForceNode,
} from "@/lib/analyses/embedding-graph-data";
import {
  captureHomeLayout,
  restoreHomeLayout,
  type HomeLayout,
} from "@/lib/analyses/embedding-graph-home-force";
import { youtubeCategoryLabel } from "@/lib/youtube-categories";
import { cn } from "@/lib/utils";
import { EmbeddingCatalogGraph3DView } from "@/components/analyses/embedding-catalog-graph-3d";

const ForceGraph2D = lazy(() => import("react-force-graph-2d"));

type GraphViewMode = "2d" | "3d";

const HOVER_HIT_PADDING = 16;
const TOOLTIP_WIDTH = 196;
const TOOLTIP_MAX_HEIGHT = 132;

interface EmbeddingCatalogGraphProps {
  data: EmbeddingGraphData | null;
  className?: string;
  hideControls?: boolean;
}

function GraphFallback() {
  return (
    <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-slate-500">
      그래프 불러오는 중…
    </div>
  );
}

function truncateTitle(title: string, max = 26): string {
  const text = title.trim() || "(제목 없음)";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function EmbeddingCatalogGraph({ data, className, hideControls = false }: EmbeddingCatalogGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(undefined);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graph3dRef = useRef<any>(undefined);
  const homeLayoutRef = useRef<HomeLayout>(new Map());
  const homeCapturedRef = useRef(false);
  const allowHomeCaptureRef = useRef(false);
  const [dimensions, setDimensions] = useState({ width: 640, height: 400 });
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [layoutReady, setLayoutReady] = useState(false);
  const [viewMode, setViewMode] = useState<GraphViewMode>("2d");

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return toCatalogForceGraph(data, categoryFilter);
  }, [data, categoryFilter]);

  const colors = useMemo(
    () => constellationCategoryColorMap(data?.nodes.map((n) => n.category_id) ?? []),
    [data],
  );

  const legend = useMemo(() => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const node of data.nodes) {
      counts.set(node.category_id, (counts.get(node.category_id) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([id, count]) => ({
        id,
        label: youtubeCategoryLabel(id),
        count,
        color: colors.get(id) ?? "#94a3b8",
      }));
  }, [data, colors]);

  const nodeById = useMemo(() => {
    const map = new Map<string, NonNullable<typeof data>["nodes"][number]>();
    for (const node of data?.nodes ?? []) {
      map.set(node.id, node);
    }
    return map;
  }, [data]);

  const highlightIds = useMemo(() => {
    if (!hoveredId) return null;
    return neighborIdSet(hoveredId, graphData.links);
  }, [hoveredId, graphData.links]);

  const hoverNeighbors = useMemo(() => {
    if (!hoveredId) return [];
    const minSimilarity = data?.min_similarity ?? 0.6;
    return sortedNeighborsBySimilarity(hoveredId, graphData.links).filter(
      (n) => n.similarity >= minSimilarity,
    );
  }, [hoveredId, graphData.links, data?.min_similarity]);

  const hoveredNode = graphData.nodes.find((n) => n.id === hoveredId);
  const fullHoveredNode = hoveredId ? nodeById.get(hoveredId) : undefined;

  const captureHomeIfReady = useCallback(() => {
    if (homeCapturedRef.current || !allowHomeCaptureRef.current) return;
    const layout = captureHomeLayout(graphData.nodes);
    if (layout.size === 0) return;
    homeLayoutRef.current = layout;
    homeCapturedRef.current = true;
    setLayoutReady(true);
  }, [graphData.nodes]);

  const handleEngineStop = useCallback(() => {
    captureHomeIfReady();
  }, [captureHomeIfReady]);

  const handleViewModeChange = useCallback((mode: GraphViewMode) => {
    setViewMode(mode);
    setHoveredId(null);
    setTooltipPos(null);
  }, []);

  const handleZoomToFit = useCallback(() => {
    if (viewMode === "2d") {
      graphRef.current?.zoomToFit(300, 48);
      return;
    }
    graph3dRef.current?.zoomToFit(400, 80);
  }, [viewMode]);

  const handleResetLayout = useCallback(() => {
    if (!restoreHomeLayout(graphData.nodes, homeLayoutRef.current)) return;
    graphRef.current?.zoomToFit(300, 48);
  }, [graphData.nodes]);

  const updateTooltipPos = useCallback(() => {
    if (!hoveredId || !graphRef.current) {
      setTooltipPos(null);
      return;
    }
    const node = graphData.nodes.find((n) => n.id === hoveredId);
    if (!node || node.x == null || node.y == null) return;

    const { x, y } = graphRef.current.graph2ScreenCoords(node.x, node.y);
    const offsetY = (node.val ?? 4) + 10;
    const half = TOOLTIP_WIDTH / 2;
    const clampedX = Math.max(half + 4, Math.min(dimensions.width - half - 4, x));
    const maxY = dimensions.height - TOOLTIP_MAX_HEIGHT - 4;
    const clampedY = Math.min(maxY, y + offsetY);

    setTooltipPos({ x: clampedX, y: Math.max(4, clampedY) });
  }, [hoveredId, graphData.nodes, dimensions.width, dimensions.height]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      setDimensions({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(320, Math.floor(rect.height)),
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    homeLayoutRef.current = new Map();
    homeCapturedRef.current = false;
    allowHomeCaptureRef.current = false;
    setLayoutReady(false);
    setHoveredId(null);
    setTooltipPos(null);

    let captureTimer: number | undefined;
    const fitTimer = window.setTimeout(() => {
      graphRef.current?.zoomToFit(400, 48);
      captureTimer = window.setTimeout(() => {
        allowHomeCaptureRef.current = true;
        if (homeCapturedRef.current) return;
        const layout = captureHomeLayout(graphData.nodes);
        if (layout.size === 0) return;
        homeLayoutRef.current = layout;
        homeCapturedRef.current = true;
        setLayoutReady(true);
      }, 450);
    }, 800);

    return () => {
      window.clearTimeout(fitTimer);
      if (captureTimer != null) window.clearTimeout(captureTimer);
    };
  }, [graphData]);

  useEffect(() => {
    updateTooltipPos();
  }, [hoveredId, updateTooltipPos, dimensions]);

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as CatalogForceNode;
      const dimmed = highlightIds !== null && !highlightIds.has(n.id);
      const x = n.x ?? 0;
      const y = n.y ?? 0;
      const radius = n.val;
      const fill = dimmed ? "#5a6880" : n.color;
      const isHovered = n.id === hoveredId;

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.globalAlpha = dimmed ? 0.25 : 0.95;
      ctx.fill();

      if (isHovered) {
        ctx.beginPath();
        ctx.arc(x, y, radius + 1.2 / globalScale, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
        ctx.lineWidth = 1 / globalScale;
        ctx.globalAlpha = 1;
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
    },
    [highlightIds, hoveredId],
  );

  const paintLink = useCallback(
    (link: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const l = link as CatalogForceLink & {
        source: CatalogForceNode;
        target: CatalogForceNode;
      };
      const source = l.source;
      const target = l.target;
      if (source.x == null || source.y == null || target.x == null || target.y == null) return;

      const sourceId = source.id;
      const targetId = target.id;
      const inFocus =
        !highlightIds ||
        (highlightIds.has(sourceId) && highlightIds.has(targetId));
      const sim = l.similarity ?? 0.6;
      const alpha = inFocus
        ? highlightIds
          ? 0.62 + (sim - 0.6) * 0.28
          : 0.38 + (sim - 0.6) * 0.2
        : 0.16;

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.strokeStyle = inFocus
        ? `rgba(255, 255, 255, ${alpha})`
        : "rgba(255, 255, 255, 0.12)";
      ctx.lineWidth = Math.max(0.24, (inFocus && highlightIds ? 0.8 : 0.58) / globalScale);
      ctx.lineCap = "round";
      ctx.stroke();
    },
    [highlightIds],
  );

  if (!data || data.total === 0) {
    return (
      <div
        className={cn(
          "border-border text-muted-foreground flex min-h-[280px] items-center justify-center rounded-2xl border bg-card p-4 text-xs",
          className,
        )}
      >
        임베딩이 있는 시청 catalog가 없습니다.
      </div>
    );
  }

  return (
    <div className={cn("border-border rounded-2xl border bg-card p-4", className)}>
      {!hideControls && (
        <>
          <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold">시청 그래프</p>
              <p className="text-muted-foreground text-xs">
                영상 {data.total}개 · 유사도 60% 이상 · 노드당 최대 5개 연결
              </p>
            </div>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground text-[10px] underline-offset-2 hover:underline"
              onClick={handleZoomToFit}
            >
              전체 보기
            </button>
          </div>

          <div className="flex flex-wrap gap-1.5 pb-3">
            <button
              type="button"
              onClick={() => setCategoryFilter(null)}
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-[10px]",
                categoryFilter === null
                  ? "border-foreground bg-foreground text-background"
                  : "border-border text-muted-foreground",
              )}
            >
              전체
            </button>
            {legend.slice(0, 8).map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() =>
                  setCategoryFilter((prev) => (prev === item.id ? null : item.id))
                }
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px]",
                  categoryFilter === item.id
                    ? "border-transparent text-white"
                    : "border-border text-muted-foreground",
                )}
                style={
                  categoryFilter === item.id ? { backgroundColor: item.color } : undefined
                }
              >
                <span className="size-2 rounded-full" style={{ backgroundColor: item.color }} />
                {item.label} ({item.count})
              </button>
            ))}
          </div>
        </>
      )}

      <div
        ref={containerRef}
        className="relative h-[min(420px,52vh)] min-h-[320px] w-full overflow-hidden rounded-xl border border-slate-800"
        style={{
          backgroundColor: "#03050a",
          backgroundImage: [
            "radial-gradient(ellipse 70% 55% at 52% 42%, rgba(28,36,58,0.38) 0%, transparent 72%)",
            "radial-gradient(ellipse 40% 35% at 20% 75%, rgba(32,24,48,0.18) 0%, transparent 70%)",
          ].join(", "),
        }}
      >
        {!hideControls && (
          <div
            className="absolute left-2 top-2 z-20 flex rounded-md border border-white/10 bg-[#0a0f1a]/80 p-0.5 shadow-sm backdrop-blur-sm"
            role="tablist"
            aria-label="그래프 보기 전환"
          >
            {(["2d", "3d"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                role="tab"
                aria-selected={viewMode === mode}
                onClick={() => handleViewModeChange(mode)}
                className={cn(
                  "rounded px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide transition-colors",
                  viewMode === mode
                    ? "bg-white/15 text-white"
                    : "text-slate-400 hover:text-slate-200",
                )}
              >
                {mode}
              </button>
            ))}
          </div>
        )}

        {!hideControls && (
          <button
            type="button"
            title="레이아웃 원상복구"
            aria-label="레이아웃 원상복구"
            disabled={!layoutReady || viewMode !== "2d"}
            onClick={handleResetLayout}
            className={cn(
              "absolute right-2 top-2 z-20 flex size-7 items-center justify-center rounded-md border border-white/10 bg-[#0a0f1a]/80 text-slate-300 shadow-sm backdrop-blur-sm transition-colors",
              layoutReady && viewMode === "2d"
                ? "hover:border-white/20 hover:bg-[#121a2a] hover:text-white"
                : "pointer-events-none opacity-0",
            )}
          >
            <RotateCcw className="size-3.5" strokeWidth={2} />
          </button>
        )}

        <div
          className={cn("absolute inset-0 z-0", viewMode !== "2d" && "hidden")}
          aria-hidden={viewMode !== "2d"}
        >
          <Suspense fallback={<GraphFallback />}>
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={graphData}
              backgroundColor="transparent"
              nodeId="id"
              nodeLabel={() => ""}
              nodeCanvasObject={paintNode}
              linkCanvasObject={paintLink}
              linkCanvasObjectMode={() => "replace"}
              nodePointerAreaPaint={(node, color, ctx) => {
                const n = node as CatalogForceNode;
                ctx.beginPath();
                ctx.arc(n.x ?? 0, n.y ?? 0, n.val + HOVER_HIT_PADDING, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
              }}
              d3AlphaDecay={0.028}
              d3VelocityDecay={0.35}
              cooldownTicks={120}
              onEngineStop={handleEngineStop}
              onRenderFramePost={() => {
                if (hoveredId) updateTooltipPos();
              }}
              onZoom={updateTooltipPos}
              onNodeHover={(node) => {
                const n = node as CatalogForceNode | null;
                setHoveredId(n?.id ?? null);
              }}
              onBackgroundClick={() => setHoveredId(null)}
            />
          </Suspense>

          {viewMode === "2d" && hoveredId && tooltipPos && fullHoveredNode && hoveredNode && (
            <div
              className="pointer-events-none absolute z-10"
              style={{
                left: tooltipPos.x,
                top: tooltipPos.y,
                width: TOOLTIP_WIDTH,
                transform: "translateX(-50%)",
              }}
            >
              <div className="overflow-hidden rounded-md border border-white/15 bg-[#0a0f1a]/92 shadow-lg shadow-black/40 backdrop-blur-sm">
                <p className="border-b border-white/10 px-2 py-1 text-[10px] font-medium leading-snug text-slate-100">
                  {truncateTitle(fullHoveredNode.title || hoveredNode.name, 30)}
                </p>
                {hoverNeighbors.length > 0 ? (
                  <ul className="max-h-[104px] space-y-0.5 overflow-y-auto px-2 py-1">
                    {hoverNeighbors.map((neighbor) => {
                      const item = nodeById.get(neighbor.id);
                      const title = truncateTitle(item?.title ?? "", 22);
                      const pct = Math.round(neighbor.similarity * 100);
                      return (
                        <li
                          key={neighbor.id}
                          className="flex items-center justify-between gap-2 text-[9px] leading-tight"
                        >
                          <span className="min-w-0 truncate text-slate-200">{title}</span>
                          <span className="shrink-0 tabular-nums text-slate-400">{pct}%</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="px-2 py-1.5 text-[9px] text-slate-500">유사 영상 없음</p>
                )}
              </div>
            </div>
          )}
        </div>

        {viewMode === "3d" && (
          <EmbeddingCatalogGraph3DView
            data={data}
            categoryFilter={categoryFilter}
            nodeById={nodeById}
            minSimilarity={data.min_similarity}
            width={dimensions.width}
            height={dimensions.height}
            graphRef={graph3dRef}
          />
        )}
      </div>

      {!hideControls && (
        <p className="text-muted-foreground mt-2 text-[10px]">
          노드 {graphData.nodes.length} · 연결 {graphData.links.length} ·{" "}
          {viewMode === "2d" ? "드래그·줌 지원" : "드래그 회전·휠 확대"}
        </p>
      )}
    </div>
  );
}
