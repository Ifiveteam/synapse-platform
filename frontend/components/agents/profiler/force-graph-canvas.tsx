"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  buildGraphData,
  formatNodeType,
  linkColor,
  neighborIds,
  nodeColor,
  type ForceGraphLink,
  type ForceGraphNode,
} from "@/lib/profiler/graph-data";
import type { GraphViewData } from "@/lib/types/profiler";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="text-muted-foreground flex h-full items-center justify-center text-sm">
      그래프 렌더링 중…
    </div>
  ),
});

interface ForceGraphCanvasProps {
  graph: GraphViewData;
}

export function ForceGraphCanvas({ graph }: ForceGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(undefined);

  const [dimensions, setDimensions] = useState({ width: 800, height: 560 });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const graphData = useMemo(() => buildGraphData(graph), [graph]);

  const highlightIds = useMemo(() => {
    if (!selectedId) return null;
    return neighborIds(selectedId, graphData.links);
  }, [selectedId, graphData.links]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setDimensions({
        width: Math.max(320, Math.floor(entry.contentRect.width)),
        height: Math.max(440, Math.floor(entry.contentRect.height)),
      });
    });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setSelectedId(null);
    const timer = window.setTimeout(() => {
      graphRef.current?.zoomToFit(500, 60);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [graph]);

  const paintNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as ForceGraphNode;
      const isAxis = n.type === "axis";
      const radius = isAxis ? n.val * 1.1 : n.val;
      const dimmed = highlightIds !== null && !highlightIds.has(n.id);
      const color = nodeColor(n.type, n.id);

      ctx.beginPath();
      ctx.arc(n.x ?? 0, n.y ?? 0, radius, 0, 2 * Math.PI);
      ctx.fillStyle = dimmed ? "rgba(30,41,59,0.5)" : color;
      ctx.fill();

      if (!dimmed) {
        ctx.strokeStyle = isAxis ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.25)";
        ctx.lineWidth = (isAxis ? 2 : 1) / globalScale;
        ctx.stroke();
      }

      if (globalScale > 0.7 && !dimmed && !isAxis) {
        ctx.font = `${Math.max(8, 9 / globalScale)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillStyle = "rgba(248,250,252,0.85)";
        ctx.fillText(
          n.name.slice(0, 10),
          n.x ?? 0,
          (n.y ?? 0) + radius + 8 / globalScale,
        );
      }
    },
    [highlightIds],
  );

  const getLinkColor = useCallback(
    (link: { source?: unknown; target?: unknown; relation?: string }) => {
      const source =
        typeof link.source === "object" && link.source !== null && "id" in link.source
          ? String((link.source as ForceGraphNode).id)
          : String(link.source);
      const target =
        typeof link.target === "object" && link.target !== null && "id" in link.target
          ? String((link.target as ForceGraphNode).id)
          : String(link.target);
      const active =
        !highlightIds || (highlightIds.has(source) && highlightIds.has(target));
      return linkColor(String(link.relation ?? ""), active);
    },
    [highlightIds],
  );

  const selectedNode = graphData.nodes.find((node) => node.id === selectedId);

  return (
    <div className="space-y-3">
      <p className="text-muted-foreground text-xs">
        {graph.kind === "taste"
          ? "태그·채널·축 노드가 무방향 엣지로 연결됩니다."
          : "도메인 노드가 무방향 연관으로 연결됩니다."}{" "}
        노드 클릭 시 이웃을 강조합니다.
      </p>

      <div
        ref={containerRef}
        className="relative h-[min(72vh,600px)] w-full overflow-hidden rounded-xl border border-violet-950/60 bg-gradient-to-b from-[#0c0f1a] to-[#070b14] shadow-inner"
      >
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeId="id"
          nodeLabel={(node) => {
            const n = node as ForceGraphNode;
            return `${n.name} (${formatNodeType(n.type)})`;
          }}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            const n = node as ForceGraphNode;
            ctx.beginPath();
            ctx.arc(n.x ?? 0, n.y ?? 0, n.val + 2, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          linkColor={(link) => getLinkColor(link)}
          linkWidth={(link) => {
            const relation = (link as ForceGraphLink).relation;
            const weight = (link as ForceGraphLink).weight;
            const max = Math.max(...graphData.links.map((l) => l.weight), 1);
            const base = relation === "maps_to" ? 1.8 : 0.8;
            return base + (weight / max) * 2;
          }}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.35}
          cooldownTicks={80}
          onNodeClick={(node) => {
            const n = node as ForceGraphNode;
            setSelectedId((prev) => (prev === n.id ? null : n.id));
          }}
          onBackgroundClick={() => setSelectedId(null)}
        />

        <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-2 text-[10px] text-slate-400">
          {graph.kind === "taste" ? (
            <>
              <span className="rounded-full bg-slate-900/85 px-2 py-0.5 text-violet-300">
                ● 축
              </span>
              <span className="rounded-full bg-slate-900/85 px-2 py-0.5 text-sky-300">
                ● 태그
              </span>
              <span className="rounded-full bg-slate-900/85 px-2 py-0.5 text-emerald-300">
                ● 채널
              </span>
            </>
          ) : (
            <span className="rounded-full bg-slate-900/85 px-2 py-0.5 text-orange-300">
              ● 도메인
            </span>
          )}
          <span className="rounded-full bg-slate-900/85 px-2 py-0.5">↔ 무방향</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
        <p>
          무방향 force · 노드 {graphData.nodes.length} · 엣지 {graphData.links.length}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className="hover:text-foreground underline-offset-2 hover:underline"
            onClick={() => graphRef.current?.zoomToFit(300, 60)}
          >
            전체 보기
          </button>
          <button
            type="button"
            className="hover:text-foreground underline-offset-2 hover:underline"
            onClick={() => setSelectedId(null)}
          >
            선택 해제
          </button>
        </div>
      </div>

      {selectedNode && (
        <div className="rounded-lg border bg-card p-4 text-sm">
          <p className="font-medium">{selectedNode.name}</p>
          <p className="text-muted-foreground mt-1">
            {formatNodeType(selectedNode.type)} · weight {selectedNode.weight.toFixed(0)}
          </p>
        </div>
      )}
    </div>
  );
}
