import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type RefObject } from "react";

import type { EmbeddingGraphData, EmbeddingGraphNode } from "@/api/indexer";
import {
  neighborIdSet,
  sortedNeighborsBySimilarity,
  toCatalogForceGraph,
  type CatalogForceNode,
} from "@/lib/analyses/embedding-graph-data";
import { youtubeCategoryLabel } from "@/lib/youtube-categories";

const ForceGraph3D = lazy(() => import("react-force-graph-3d"));

const TOOLTIP_WIDTH = 196;
const INITIAL_ZOOM_FALLBACK_MS = 2200;

export interface EmbeddingCatalogGraph3DViewProps {
  data: EmbeddingGraphData;
  categoryFilter: string | null;
  nodeById: Map<string, EmbeddingGraphNode>;
  minSimilarity?: number;
  width: number;
  height: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  graphRef?: RefObject<any>;
}

function GraphFallback() {
  return (
    <div className="flex h-full min-h-[200px] items-center justify-center text-sm text-slate-500">
      3D 그래프 불러오는 중…
    </div>
  );
}

function truncateTitle(title: string, max = 26): string {
  const text = title.trim() || "(제목 없음)";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function EmbeddingCatalogGraph3DView({
  data,
  categoryFilter,
  nodeById,
  minSimilarity = 0.6,
  width,
  height,
  graphRef: graphRefProp,
}: EmbeddingCatalogGraph3DViewProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const localGraphRef = useRef<any>(undefined);
  const graphRef = graphRefProp ?? localGraphRef;
  const linkForceReadyRef = useRef(false);
  const initialZoomDoneRef = useRef(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const graphData = useMemo(() => {
    const base = toCatalogForceGraph(data, categoryFilter);
    return {
      nodes: base.nodes.map((node) => ({ ...node })),
      links: base.links.map((link) => ({ ...link })),
    };
  }, [data, categoryFilter]);

  const highlightIds = useMemo(() => {
    if (!hoveredId) return null;
    return neighborIdSet(hoveredId, graphData.links);
  }, [hoveredId, graphData.links]);

  const hoverNeighbors = useMemo(() => {
    if (!hoveredId) return [];
    return sortedNeighborsBySimilarity(hoveredId, graphData.links).filter(
      (n) => n.similarity >= minSimilarity,
    );
  }, [hoveredId, graphData.links, minSimilarity]);

  const hoveredNode = graphData.nodes.find((n) => n.id === hoveredId);
  const fullHoveredNode = hoveredId ? nodeById.get(hoveredId) : undefined;

  const runInitialZoomToFit = useCallback(() => {
    if (initialZoomDoneRef.current) return;
    initialZoomDoneRef.current = true;
    graphRef.current?.zoomToFit(500, 80);
  }, [graphRef]);

  useEffect(() => {
    setHoveredId(null);
    linkForceReadyRef.current = false;
    initialZoomDoneRef.current = false;

    const fallbackTimer = window.setTimeout(() => {
      runInitialZoomToFit();
    }, INITIAL_ZOOM_FALLBACK_MS);

    return () => window.clearTimeout(fallbackTimer);
  }, [graphData, runInitialZoomToFit]);

  const setupLinkForce = useCallback(() => {
    const linkForce = graphRef.current?.d3Force("link");
    if (!linkForce) return;
    linkForce.distance((link: { similarity?: number }) => {
      const sim = link.similarity ?? 0.6;
      return 28 + (1 - sim) * 42;
    });
  }, [graphRef]);

  const handleEngineTick = useCallback(() => {
    if (linkForceReadyRef.current) return;
    linkForceReadyRef.current = true;
    setupLinkForce();
  }, [setupLinkForce]);

  const handleEngineStop = useCallback(() => {
    runInitialZoomToFit();
  }, [runInitialZoomToFit]);

  const getNodeColor = useCallback(
    (node: object) => {
      const n = node as CatalogForceNode;
      const dimmed = highlightIds !== null && !highlightIds.has(n.id);
      return dimmed ? "#4a5568" : n.color;
    },
    [highlightIds],
  );

  const getNodeVal = useCallback((node: object) => {
    const n = node as CatalogForceNode;
    return n.isShorts ? 10 : 14;
  }, []);

  const getLinkColor = useCallback(
    (link: object) => {
      const l = link as {
        source: CatalogForceNode | string;
        target: CatalogForceNode | string;
        similarity?: number;
      };
      const sourceId = typeof l.source === "object" ? l.source.id : l.source;
      const targetId = typeof l.target === "object" ? l.target.id : l.target;
      const inFocus =
        !highlightIds || (highlightIds.has(sourceId) && highlightIds.has(targetId));
      const sim = l.similarity ?? 0.6;
      const alpha = inFocus
        ? highlightIds
          ? 0.58 + (sim - 0.6) * 0.26
          : 0.36 + (sim - 0.6) * 0.18
        : 0.14;
      return `rgba(255, 255, 255, ${alpha})`;
    },
    [highlightIds],
  );

  if (graphData.nodes.length === 0) return null;

  return (
    <div className="absolute inset-0 z-10">
      <Suspense fallback={<GraphFallback />}>
        <ForceGraph3D
          ref={graphRef}
          width={width}
          height={height}
          graphData={graphData}
          backgroundColor="rgba(0,0,0,0)"
          showNavInfo={false}
          nodeId="id"
          nodeRelSize={4}
          nodeVal={getNodeVal}
          nodeColor={getNodeColor}
          nodeLabel={(node) => {
            const n = node as CatalogForceNode;
            return `${n.name} · ${youtubeCategoryLabel(n.categoryId)}`;
          }}
          linkColor={getLinkColor}
          linkWidth={0.65}
          linkOpacity={1}
          enableNodeDrag
          d3AlphaDecay={0.028}
          d3VelocityDecay={0.35}
          cooldownTicks={120}
          onEngineTick={handleEngineTick}
          onEngineStop={handleEngineStop}
          onNodeHover={(node) => {
            const n = node as CatalogForceNode | null;
            setHoveredId(n?.id ?? null);
          }}
          onBackgroundClick={() => setHoveredId(null)}
        />
      </Suspense>

      {hoveredId && fullHoveredNode && hoveredNode && (
        <div
          className="pointer-events-none absolute right-3 top-11 z-10"
          style={{ width: TOOLTIP_WIDTH }}
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
  );
}
