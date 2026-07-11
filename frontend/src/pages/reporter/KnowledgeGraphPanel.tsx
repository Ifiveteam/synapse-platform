import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Loader2, Network } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  fetchKnowledgeGraph,
  type KnowledgeGraphData,
  type KnowledgeGraphLink,
  type KnowledgeGraphNode,
} from "@/services/reporter";

const ForceGraph2D = lazy(() => import("react-force-graph-2d"));

const DOMAIN_HUB_GROUP = "domain_hub";

const DOMAIN_COLORS: Record<string, string> = {
  "Tech/Business": "#38bdf8",
  "Content/Media": "#f472b6",
  "Lifestyle/Wellness": "#4ade80",
  "Social/Current Affairs": "#fb923c",
  "Knowledge/Education": "#a78bfa",
  "Economy/TechFin": "#facc15",
};

const HUB_NODE_COLOR = "#818cf8";
const HUB_GLOW_COLOR = "rgba(129, 140, 248, 0.45)";

function nodeColor(node: KnowledgeGraphNode): string {
  if (node.group === DOMAIN_HUB_GROUP) return HUB_NODE_COLOR;
  return DOMAIN_COLORS[node.group] ?? "#94a3b8";
}

function nodeLabel(node: KnowledgeGraphNode): string {
  const isHub = node.group === DOMAIN_HUB_GROUP;
  const role = isHub ? "도메인 허브" : node.group;
  return `${node.id}\n${role} · score ${node.val.toFixed(2)}`;
}

function linkLabel(link: KnowledgeGraphLink): string {
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
    return `${source} ↔ ${target}\n공출현 (팩트)`;
  }
  return `${source} ↔ ${target}`;
}

function GraphCanvasFallback() {
  return (
    <div className="flex h-full min-h-[420px] items-center justify-center gap-2 text-sm text-slate-400">
      <Loader2 className="size-4 animate-spin" />
      그래프 엔진 로딩 중…
    </div>
  );
}

interface KnowledgeGraphPanelProps {
  selectedDate: string;
}

export function KnowledgeGraphPanel({ selectedDate }: KnowledgeGraphPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(undefined);

  const [graphData, setGraphData] = useState<KnowledgeGraphData>({
    nodes: [],
    links: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rangeLabel, setRangeLabel] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 960, height: 520 });

  const loadGraph = useCallback(async (date: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKnowledgeGraph(date, 7);
      setGraphData(data);
      if (data.start_date && data.end_date) {
        const count =
          typeof data.snapshot_count === "number" ? data.snapshot_count : 0;
        setRangeLabel(
          `조회 기간 ${data.start_date} ~ ${data.end_date} (7일) · 실제 합산 스냅샷 ${count}일`,
        );
      } else {
        setRangeLabel(null);
      }
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
    void loadGraph(selectedDate);
  }, [selectedDate, loadGraph]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      setDimensions({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(420, Math.floor(rect.height)),
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (loading || graphData.nodes.length === 0) return;
    const timer = window.setTimeout(() => {
      graphRef.current?.zoomToFit(400, 56);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [graphData, loading]);

  const legendItems = useMemo(() => {
    const groups = new Set(
      graphData.nodes
        .filter((n) => n.group !== DOMAIN_HUB_GROUP)
        .map((n) => n.group),
    );
    return [...groups].map((group) => ({
      group,
      color: DOMAIN_COLORS[group] ?? "#94a3b8",
    }));
  }, [graphData.nodes]);

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as KnowledgeGraphNode & { x?: number; y?: number };
      const x = n.x ?? 0;
      const y = n.y ?? 0;
      const isHub = n.group === DOMAIN_HUB_GROUP;
      const radius = n.val ?? 6;
      const fill = nodeColor(n);

      if (isHub) {
        ctx.beginPath();
        ctx.arc(x, y, radius + 3 / globalScale, 0, Math.PI * 2);
        ctx.fillStyle = HUB_GLOW_COLOR;
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
        ctx.strokeStyle = "rgba(199, 210, 254, 0.85)";
        ctx.lineWidth = 1.2 / globalScale;
        ctx.stroke();
      }
    },
    [],
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

      const width = Math.max(0.3, (l.value ?? 0.5) / globalScale);
      const isSemantic = l.link_type === "semantic";
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      if (isSemantic) {
        ctx.setLineDash([4 / globalScale, 3 / globalScale]);
        ctx.strokeStyle = "rgba(129, 140, 248, 0.65)";
      } else if (l.link_type === "domain_hub") {
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(148, 163, 184, 0.28)";
      } else {
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(148, 163, 184, 0.42)";
      }
      ctx.lineWidth = width;
      ctx.lineCap = "round";
      ctx.stroke();
      ctx.setLineDash([]);
    },
    [],
  );

  const isEmpty = !loading && !error && graphData.nodes.length === 0;

  return (
    <div className="border-border bg-card rounded-2xl border p-4 shadow-sm">
      {rangeLabel && (
        <p className="text-muted-foreground mb-2 text-xs">{rangeLabel}</p>
      )}
      {legendItems.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-2.5 py-0.5 text-[10px] text-indigo-200">
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: HUB_NODE_COLOR }}
            />
            domain_hub
          </span>
          {legendItems.map((item) => (
            <span
              key={item.group}
              className="border-border inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px]"
            >
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              {item.group}
            </span>
          ))}
          <span className="border-border inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] text-slate-400">
            <span className="h-px w-3 border-t border-dashed border-indigo-400" />
            semantic
          </span>
          <span className="border-border inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] text-slate-400">
            <span className="h-px w-3 bg-slate-400" />
            cooccurrence
          </span>
        </div>
      )}

      <div
        ref={containerRef}
        className="relative h-[min(560px,68vh)] min-h-[420px] w-full overflow-hidden rounded-xl border border-slate-800"
        style={{
          backgroundColor: "#03050a",
          backgroundImage: [
            "radial-gradient(ellipse 70% 55% at 52% 42%, rgba(56,72,120,0.35) 0%, transparent 72%)",
            "radial-gradient(ellipse 40% 35% at 18% 78%, rgba(76,29,149,0.2) 0%, transparent 70%)",
          ].join(", "),
        }}
      >
        {loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#03050a]/70 backdrop-blur-[1px]">
            <Loader2 className="size-8 animate-spin text-indigo-300" />
            <p className="text-sm text-slate-300">
              {selectedDate} 기준 7일 합산 그래프 불러오는 중…
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
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void loadGraph(selectedDate)}
            >
              다시 시도
            </Button>
          </div>
        )}

        {isEmpty && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 px-6 text-center">
            <Network className="text-muted-foreground size-10" />
            <p className="text-sm font-medium text-slate-200">
              {selectedDate} 기준 최근 7일 데이터가 없습니다
            </p>
            <p className="text-muted-foreground max-w-sm text-xs">
              Aggregator 배치로 스냅샷이 쌓이면, 종료일 포함 7일을 합산한
              지식 그래프가 여기에 표시됩니다.
            </p>
          </div>
        )}

        {!error && graphData.nodes.length > 0 && (
          <Suspense fallback={<GraphCanvasFallback />}>
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={graphData}
              backgroundColor="transparent"
              nodeId="id"
              nodeVal={(node) => (node as KnowledgeGraphNode).val}
              linkWidth={(link) => (link as KnowledgeGraphLink).value}
              nodeLabel={(node) => nodeLabel(node as KnowledgeGraphNode)}
              linkLabel={(link) => linkLabel(link as KnowledgeGraphLink)}
              nodeCanvasObject={paintNode}
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
                  (n.val ?? 6) + 10,
                  0,
                  Math.PI * 2,
                );
                ctx.fillStyle = color;
                ctx.fill();
              }}
              d3AlphaDecay={0.03}
              d3VelocityDecay={0.35}
              cooldownTicks={140}
              onEngineStop={() => graphRef.current?.zoomToFit(300, 56)}
            />
          </Suspense>
        )}
      </div>

      <p
        className={cn(
          "text-muted-foreground mt-3 text-[11px]",
          loading && "opacity-60",
        )}
      >
        노드 {graphData.nodes.length} · 연결 {graphData.links.length}
        {!loading && graphData.nodes.length > 0 && " · 드래그·줌 지원"}
      </p>
    </div>
  );
}
