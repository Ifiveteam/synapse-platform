import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Loader2, Network } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DOMAIN_HUB_GROUP,
  DOMAIN_COLORS,
  DOMAIN_LABELS,
  domainLabel,
} from "@/lib/trend-domains";
import { cn } from "@/lib/utils";
import {
  fetchKnowledgeGraph,
  type KnowledgeGraphData,
  type KnowledgeGraphLink,
  type KnowledgeGraphNode,
} from "@/services/reporter";

const ForceGraph2D = lazy(() => import("react-force-graph-2d"));

/** 기본 뷰에서 유지할 공출현 엣지 상한 — 헤어볼 완화 */
const MAX_COOCCURRENCE_EDGES = 48;
/** 항상 라벨을 그릴 비허브 노드 수 (점수 상위) */
const ALWAYS_LABEL_TOP_N = 12;
/** 줌인 시 추가 라벨을 그릴 임계 globalScale */
const ZOOM_LABEL_SCALE = 1.35;

const HUB_FALLBACK_COLOR = "#94a3b8";

function hexToRgba(hex: string, alpha: number): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return `rgba(148, 163, 184, ${alpha})`;
  const r = Number.parseInt(raw.slice(0, 2), 16);
  const g = Number.parseInt(raw.slice(2, 4), 16);
  const b = Number.parseInt(raw.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function nodeColor(node: KnowledgeGraphNode): string {
  // 허브는 group이 domain_hub이고 id가 도메인명(Tech/Business 등)
  if (node.group === DOMAIN_HUB_GROUP) {
    return DOMAIN_COLORS[node.id] ?? HUB_FALLBACK_COLOR;
  }
  return DOMAIN_COLORS[node.group] ?? HUB_FALLBACK_COLOR;
}

function nodeDisplayLabel(node: KnowledgeGraphNode): string {
  if (node.group === DOMAIN_HUB_GROUP) {
    return DOMAIN_LABELS[node.id] ?? node.id;
  }
  return node.id;
}

function truncateLabel(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  return `${text.slice(0, Math.max(1, maxChars - 1))}…`;
}

function nodeHoverLabel(node: KnowledgeGraphNode): string {
  const role =
    node.group === DOMAIN_HUB_GROUP
      ? "도메인 허브"
      : domainLabel(node.group);
  return `${nodeDisplayLabel(node)}\n${role} · score ${node.val.toFixed(2)}`;
}

function linkHoverLabel(link: KnowledgeGraphLink): string {
  const source =
    typeof link.source === "string"
      ? link.source
      : ((link.source as KnowledgeGraphNode | undefined)?.id ?? "?");
  const target =
    typeof link.target === "string"
      ? link.target
      : ((link.target as KnowledgeGraphNode | undefined)?.id ?? "?");
  if (link.link_type === "semantic" && link.similarity != null) {
    return `${source} ↔ ${target}\n의미 유사도 ${link.similarity.toFixed(2)}`;
  }
  if (link.link_type === "cooccurrence") {
    return `${source} ↔ ${target}\n함께 등장 (공출현)`;
  }
  if (link.link_type === "domain_hub") {
    return `${source} ↔ ${target}\n도메인 허브 연결`;
  }
  return `${source} ↔ ${target}`;
}

function linkEndpointId(
  endpoint: KnowledgeGraphLink["source"] | KnowledgeGraphLink["target"],
): string {
  return typeof endpoint === "string"
    ? endpoint
    : ((endpoint as KnowledgeGraphNode | undefined)?.id ?? "");
}

/** 헤어볼을 줄이기 위해 허브·상위 공출현(+선택적 semantic)만 남긴다. */
function filterReadableLinks(
  links: KnowledgeGraphLink[],
  options: { showSemantic: boolean; showAllLinks: boolean },
): KnowledgeGraphLink[] {
  if (options.showAllLinks) {
    if (options.showSemantic) return links;
    return links.filter((l) => l.link_type !== "semantic");
  }

  const hubs: KnowledgeGraphLink[] = [];
  const cooccurrence: KnowledgeGraphLink[] = [];
  const semantic: KnowledgeGraphLink[] = [];

  for (const link of links) {
    if (link.link_type === "domain_hub") hubs.push(link);
    else if (link.link_type === "semantic") semantic.push(link);
    else cooccurrence.push(link);
  }

  const topCooccurrence = [...cooccurrence]
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, MAX_COOCCURRENCE_EDGES);

  const result = [...hubs, ...topCooccurrence];
  if (options.showSemantic) {
    const topSemantic = [...semantic]
      .sort(
        (a, b) =>
          (b.similarity ?? b.value ?? 0) - (a.similarity ?? a.value ?? 0),
      )
      .slice(0, Math.floor(MAX_COOCCURRENCE_EDGES / 2));
    result.push(...topSemantic);
  }
  return result;
}

function GraphCanvasFallback() {
  return (
    <div className="flex h-full min-h-[420px] items-center justify-center gap-2 text-sm text-slate-400">
      <Loader2 className="size-4 animate-spin" />
      그래프 엔진 로딩 중…
    </div>
  );
}

function rangeLabelFromData(data: KnowledgeGraphData): string | null {
  if (!data.start_date || !data.end_date) return null;
  const count = typeof data.snapshot_count === "number" ? data.snapshot_count : 0;
  return `조회 기간 ${data.start_date} ~ ${data.end_date} (14일) · 실제 합산 스냅샷 ${count}일`;
}

interface KnowledgeGraphPanelProps {
  selectedDate: string;
  /**
   * 홈 히어로 뷰 — 화면을 크게 채우고, 전체보기와 동일한 범례·토글을 제공한다.
   */
  compact?: boolean;
  /** 부모가 이미 로드한 데이터 — 있으면 자체 fetch 생략 */
  externalData?: KnowledgeGraphData;
  externalLoading?: boolean;
  externalError?: string | null;
  onRetry?: () => void;
}

export function KnowledgeGraphPanel({
  selectedDate,
  compact = false,
  externalData,
  externalLoading,
  externalError,
  onRetry,
}: KnowledgeGraphPanelProps) {
  const isControlled = externalData !== undefined;
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(undefined);

  const [graphData, setGraphData] = useState<KnowledgeGraphData>(
    externalData ?? { nodes: [], links: [] },
  );
  const [loading, setLoading] = useState(
    isControlled ? Boolean(externalLoading) : true,
  );
  const [error, setError] = useState<string | null>(
    isControlled ? (externalError ?? null) : null,
  );
  const [rangeLabel, setRangeLabel] = useState<string | null>(
    externalData ? rangeLabelFromData(externalData) : null,
  );
  const [dimensions, setDimensions] = useState({
    width: 960,
    height: compact ? 640 : 520,
  });
  const [showSemantic, setShowSemantic] = useState(false);
  const [showAllLinks, setShowAllLinks] = useState(false);
  const [showAllLabels, setShowAllLabels] = useState(false);

  const loadGraph = useCallback(async (date: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKnowledgeGraph(date, 14);
      setGraphData(data);
      setRangeLabel(rangeLabelFromData(data));
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "지식 그래프를 불러오지 못했습니다.";
      setError(message);
      setGraphData({ nodes: [], links: [] });
      setRangeLabel(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isControlled) return;
    setGraphData(externalData);
    setLoading(Boolean(externalLoading));
    setError(externalError ?? null);
    setRangeLabel(rangeLabelFromData(externalData));
  }, [isControlled, externalData, externalLoading, externalError]);

  useEffect(() => {
    if (isControlled) return;
    void loadGraph(selectedDate);
  }, [selectedDate, loadGraph, isControlled]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      setDimensions({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(compact ? 480 : 420, Math.floor(rect.height)),
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [compact]);

  const labeledNodeIds = useMemo(() => {
    const ids = new Set<string>();
    const hubs = graphData.nodes.filter((n) => n.group === DOMAIN_HUB_GROUP);
    const topics = [...graphData.nodes]
      .filter((n) => n.group !== DOMAIN_HUB_GROUP)
      .sort((a, b) => b.val - a.val)
      .slice(0, ALWAYS_LABEL_TOP_N);
    for (const n of hubs) ids.add(n.id);
    for (const n of topics) ids.add(n.id);
    return ids;
  }, [graphData.nodes]);

  const displayData = useMemo(() => {
    const links = filterReadableLinks(graphData.links, {
      showSemantic,
      showAllLinks,
    });
    return {
      nodes: graphData.nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({
        ...l,
        source: linkEndpointId(l.source),
        target: linkEndpointId(l.target),
      })),
    };
  }, [graphData, showSemantic, showAllLinks]);

  const configureForces = useCallback(() => {
    const fg = graphRef.current;
    if (!fg) return;
    const charge = fg.d3Force("charge");
    if (charge?.strength) charge.strength(compact ? -200 : -180);
    const link = fg.d3Force("link");
    if (link?.distance) link.distance(compact ? 80 : 72);
    const center = fg.d3Force("center");
    if (center?.strength) center.strength(0.05);
  }, [compact]);

  useEffect(() => {
    if (loading || displayData.nodes.length === 0) return;
    const timer = window.setTimeout(() => {
      configureForces();
      graphRef.current?.zoomToFit(400, compact ? 64 : 72);
    }, 700);
    return () => window.clearTimeout(timer);
  }, [displayData, loading, configureForces, compact]);

  const legendItems = useMemo(() => {
    const groups = new Set(
      graphData.nodes
        .filter((n) => n.group !== DOMAIN_HUB_GROUP)
        .map((n) => n.group),
    );
    return [...groups].map((group) => ({
      group,
      label: domainLabel(group),
      color: DOMAIN_COLORS[group] ?? "#94a3b8",
    }));
  }, [graphData.nodes]);

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as KnowledgeGraphNode & { x?: number; y?: number };
      const x = n.x ?? 0;
      const y = n.y ?? 0;
      const isHub = n.group === DOMAIN_HUB_GROUP;
      const radius = Math.max(4, n.val ?? 6);
      const fill = nodeColor(n);

      if (isHub) {
        ctx.beginPath();
        ctx.arc(x, y, radius + 3 / globalScale, 0, Math.PI * 2);
        ctx.fillStyle = hexToRgba(fill, 0.4);
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.globalAlpha = isHub ? 1 : 0.92;
      ctx.fill();
      ctx.globalAlpha = 1;

      if (isHub) {
        ctx.beginPath();
        ctx.arc(x, y, radius + 1.5 / globalScale, 0, Math.PI * 2);
        ctx.strokeStyle = hexToRgba(fill, 0.9);
        ctx.lineWidth = 1.2 / globalScale;
        ctx.stroke();
      }

      const shouldLabel =
        showAllLabels ||
        labeledNodeIds.has(n.id) ||
        globalScale >= ZOOM_LABEL_SCALE;
      if (!shouldLabel) return;

      const fontSize = Math.max(
        7.5,
        (isHub ? 8.5 : 8) / Math.min(globalScale, 2.2),
      );
      const maxChars = isHub ? 14 : globalScale >= ZOOM_LABEL_SCALE ? 14 : 12;
      const label = truncateLabel(nodeDisplayLabel(n), maxChars);
      ctx.font = `${isHub ? "600" : "500"} ${fontSize}px ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";

      const textY = y + radius + 2.5 / globalScale;
      const metrics = ctx.measureText(label);
      const padX = 3 / globalScale;
      const padY = 1.5 / globalScale;
      const boxW = metrics.width + padX * 2;
      const boxH = fontSize + padY * 2;

      ctx.fillStyle = "rgba(3, 5, 10, 0.7)";
      ctx.fillRect(x - boxW / 2, textY - padY, boxW, boxH);

      ctx.fillStyle = isHub ? "#f8fafc" : "#cbd5e1";
      ctx.fillText(label, x, textY);
    },
    [labeledNodeIds, showAllLabels],
  );

  const paintLink = useCallback(
    (link: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const l = link as KnowledgeGraphLink & {
        source: KnowledgeGraphNode & { x?: number; y?: number };
        target: KnowledgeGraphNode & { x?: number; y?: number };
      };
      const source = l.source;
      const target = l.target;
      if (
        source.x == null ||
        source.y == null ||
        target.x == null ||
        target.y == null
      ) {
        return;
      }

      const width = Math.max(
        0.35,
        Math.min(2.2, (l.value ?? 0.5) * 1.1) / globalScale,
      );
      const isSemantic = l.link_type === "semantic";
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      if (isSemantic) {
        ctx.setLineDash([4 / globalScale, 3 / globalScale]);
        ctx.strokeStyle = "rgba(129, 140, 248, 0.45)";
      } else if (l.link_type === "domain_hub") {
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(148, 163, 184, 0.22)";
      } else {
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(148, 163, 184, 0.5)";
      }
      ctx.lineWidth = width;
      ctx.lineCap = "round";
      ctx.stroke();
      ctx.setLineDash([]);
    },
    [],
  );

  const isEmpty = !loading && !error && graphData.nodes.length === 0;
  const hiddenLinkCount = Math.max(
    0,
    graphData.links.length - displayData.links.length,
  );

  const handleRetry = () => {
    if (onRetry) onRetry();
    else void loadGraph(selectedDate);
  };

  return (
    <div
      className={cn(
        compact
          ? "flex flex-col gap-3"
          : "border-border bg-card rounded-2xl border p-4 shadow-sm",
      )}
    >
      {(rangeLabel || compact) && rangeLabel && (
        <p
          className={cn(
            "text-muted-foreground text-xs",
            !compact && "mb-2",
          )}
        >
          {rangeLabel}
        </p>
      )}

      <div
        className={cn(
          "flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between",
          !compact && "mb-3",
        )}
      >
        {legendItems.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px]",
                compact
                  ? "bg-muted/60 text-muted-foreground"
                  : "border-border border text-slate-400",
              )}
            >
              큰 원 · 도메인 허브
            </span>
            {legendItems.map((item) => (
              <span
                key={item.group}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px]",
                  compact
                    ? "bg-muted/60 text-muted-foreground"
                    : "border-border border",
                )}
              >
                <span
                  className="size-2 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                {item.label}
              </span>
            ))}
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px]",
                compact
                  ? "bg-muted/60 text-muted-foreground"
                  : "border-border border text-slate-400",
              )}
            >
              <span className="h-px w-3 bg-slate-400" />
              함께 등장
            </span>
            {(showSemantic || showAllLinks) && (
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px]",
                  compact
                    ? "bg-muted/60 text-muted-foreground"
                    : "border-border border text-slate-400",
                )}
              >
                <span className="h-px w-3 border-t border-dashed border-indigo-400" />
                의미 유사
              </span>
            )}
          </div>
        ) : (
          <div />
        )}

        {graphData.nodes.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              type="button"
              size="sm"
              variant={showSemantic ? "default" : "outline"}
              className={cn(
                "h-7 px-2.5 text-[11px]",
                compact && !showSemantic && "border-border/70 bg-transparent",
              )}
              onClick={() => setShowSemantic((v) => !v)}
            >
              의미 유사
            </Button>
            <Button
              type="button"
              size="sm"
              variant={showAllLinks ? "default" : "outline"}
              className={cn(
                "h-7 px-2.5 text-[11px]",
                compact && !showAllLinks && "border-border/70 bg-transparent",
              )}
              onClick={() => setShowAllLinks((v) => !v)}
            >
              모든 연결
            </Button>
            <Button
              type="button"
              size="sm"
              variant={showAllLabels ? "default" : "outline"}
              className={cn(
                "h-7 px-2.5 text-[11px]",
                compact && !showAllLabels && "border-border/70 bg-transparent",
              )}
              onClick={() => setShowAllLabels((v) => !v)}
            >
              모든 라벨
            </Button>
          </div>
        )}
      </div>

      <div
        ref={containerRef}
        className={cn(
          "relative w-full overflow-hidden",
          compact
            ? "h-[min(720px,78vh)] min-h-[520px] rounded-2xl"
            : "h-[min(560px,68vh)] min-h-[420px] rounded-xl border border-slate-800",
        )}
        style={{
          backgroundColor: compact ? "#0a0a0a" : "#03050a",
          backgroundImage: compact
            ? "radial-gradient(ellipse 55% 45% at 50% 45%, rgba(40,48,72,0.45) 0%, transparent 70%)"
            : [
                "radial-gradient(ellipse 70% 55% at 52% 42%, rgba(56,72,120,0.35) 0%, transparent 72%)",
                "radial-gradient(ellipse 40% 35% at 18% 78%, rgba(76,29,149,0.2) 0%, transparent 70%)",
              ].join(", "),
        }}
      >
        {loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#03050a]/70 backdrop-blur-[1px]">
            <Loader2 className="size-8 animate-spin text-indigo-300" />
            <p className="text-sm text-slate-300">
              {selectedDate} 기준 14일 합산 그래프 불러오는 중…
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <AlertCircle className="size-10 text-rose-400" />
            <div>
              <p className="text-sm font-medium text-slate-100">
                데이터를 불러오지 못했습니다
              </p>
              <p className="text-muted-foreground mt-1 max-w-md text-xs">
                {error}
              </p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={handleRetry}>
              다시 시도
            </Button>
          </div>
        )}

        {isEmpty && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 px-6 text-center">
            <Network className="text-muted-foreground size-10" />
            <p className="text-sm font-medium text-slate-200">
              {selectedDate} 기준 최근 14일 데이터가 없습니다
            </p>
            <p className="text-muted-foreground max-w-sm text-xs">
              Aggregator 배치로 스냅샷이 쌓이면, 종료일 포함 14일을 합산한
              지식 그래프가 여기에 표시됩니다.
            </p>
          </div>
        )}

        {!error && displayData.nodes.length > 0 && (
          <Suspense fallback={<GraphCanvasFallback />}>
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={displayData}
              backgroundColor="transparent"
              nodeId="id"
              nodeVal={(node) => (node as KnowledgeGraphNode).val}
              linkWidth={(link) => (link as KnowledgeGraphLink).value}
              nodeLabel={(node) => nodeHoverLabel(node as KnowledgeGraphNode)}
              linkLabel={(link) => linkHoverLabel(link as KnowledgeGraphLink)}
              nodeCanvasObject={paintNode}
              nodeCanvasObjectMode={() => "replace"}
              linkCanvasObject={paintLink}
              linkCanvasObjectMode={() => "replace"}
              nodePointerAreaPaint={(node, color, ctx) => {
                const n = node as KnowledgeGraphNode & {
                  x?: number;
                  y?: number;
                };
                ctx.beginPath();
                ctx.arc(
                  n.x ?? 0,
                  n.y ?? 0,
                  (n.val ?? 6) + 12,
                  0,
                  Math.PI * 2,
                );
                ctx.fillStyle = color;
                ctx.fill();
              }}
              d3AlphaDecay={0.028}
              d3VelocityDecay={0.32}
              cooldownTicks={160}
              onEngineStop={() => {
                configureForces();
                graphRef.current?.zoomToFit(300, compact ? 64 : 72);
              }}
            />
          </Suspense>
        )}
      </div>

      <p
        className={cn(
          "text-muted-foreground text-[11px]",
          compact ? "mt-1" : "mt-3",
          loading && "opacity-60",
        )}
      >
        노드 {graphData.nodes.length} · 표시 연결 {displayData.links.length}
        {hiddenLinkCount > 0 && ` · 숨김 ${hiddenLinkCount}`}
        {!loading && graphData.nodes.length > 0 && " · 드래그·줌 지원"}
        {!showAllLabels &&
          graphData.nodes.length > 0 &&
          " · 허브·상위 키워드 라벨 표시 (줌인 시 더 보임)"}
      </p>
    </div>
  );
}
