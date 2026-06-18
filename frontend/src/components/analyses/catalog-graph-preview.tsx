import { useMemo, useState } from "react";

import type { CatalogGraphSummary } from "@/api/indexer";
import {
  buildCatalogGraphFromSummary,
  type CatalogGraphNode,
} from "@/lib/analyses/catalog-graph";
import { cn } from "@/lib/utils";

const NODE_FILL: Record<CatalogGraphNode["kind"], string> = {
  center: "var(--primary)",
  category: "#8b5cf6",
  channel: "#34d399",
};

interface CatalogGraphPreviewProps {
  summary: CatalogGraphSummary | null;
  className?: string;
}

export function CatalogGraphPreview({ summary, className }: CatalogGraphPreviewProps) {
  const [hoverId, setHoverId] = useState<string | null>(null);

  const layout = useMemo(
    () => (summary ? buildCatalogGraphFromSummary(summary) : { nodes: [], edges: [], total: 0 }),
    [summary],
  );

  const nodeMap = useMemo(
    () => Object.fromEntries(layout.nodes.map((n) => [n.id, n])),
    [layout.nodes],
  );

  const neighborIds = useMemo(() => {
    if (!hoverId) return null;
    const ids = new Set<string>([hoverId]);
    for (const edge of layout.edges) {
      if (edge.from === hoverId) ids.add(edge.to);
      if (edge.to === hoverId) ids.add(edge.from);
    }
    return ids;
  }, [hoverId, layout.edges]);

  if (layout.total === 0) {
    return (
      <div
        className={cn(
          "border-border text-muted-foreground flex min-h-[200px] items-center justify-center rounded-2xl border bg-card p-4 text-xs",
          className,
        )}
      >
        시청 catalog가 없습니다. Takeout 또는 Drive 업로드 후 다시 확인하세요.
      </div>
    );
  }

  return (
    <div className={cn("border-border rounded-2xl border bg-card p-4", className)}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">시청 그래프</p>
          <p className="text-muted-foreground text-xs">
            catalog {layout.total}건 · 상위 카테고리·채널 연결
          </p>
        </div>
        <div className="text-muted-foreground flex flex-wrap gap-3 text-[10px]">
          <span className="inline-flex items-center gap-1">
            <span className="bg-primary inline-block size-2 rounded-full" />
            시청
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block size-2 rounded-full bg-violet-500" />
            카테고리
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block size-2 rounded-full bg-emerald-400" />
            채널
          </span>
        </div>
      </div>

      <div className="relative min-h-[220px] w-full">
        <svg
          viewBox="0 0 720 260"
          className="h-full w-full"
          role="img"
          aria-label="시청 catalog 그래프"
        >
          {layout.edges.map((edge, i) => {
            const from = nodeMap[edge.from];
            const to = nodeMap[edge.to];
            if (!from || !to) return null;
            const dimmed =
              neighborIds !== null &&
              !neighborIds.has(edge.from) &&
              !neighborIds.has(edge.to);
            return (
              <line
                key={i}
                x1={from.cx}
                y1={from.cy}
                x2={to.cx}
                y2={to.cy}
                stroke="var(--border)"
                strokeWidth={dimmed ? 1 : 1.5}
                opacity={dimmed ? 0.25 : 0.85}
              />
            );
          })}

          {layout.nodes.map((node) => {
            const dimmed = neighborIds !== null && !neighborIds.has(node.id);
            const isCenter = node.kind === "center";
            return (
              <g
                key={node.id}
                className="cursor-default"
                onMouseEnter={() => setHoverId(node.id)}
                onMouseLeave={() => setHoverId(null)}
              >
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={node.r}
                  fill={NODE_FILL[node.kind]}
                  opacity={dimmed ? 0.35 : 0.92}
                  stroke={hoverId === node.id ? "#18181b" : "transparent"}
                  strokeWidth={2}
                />
                {(isCenter || node.r >= 13) && (
                  <text
                    x={node.cx}
                    y={node.cy + (isCenter ? 4 : 3)}
                    textAnchor="middle"
                    className="fill-white font-semibold select-none"
                    style={{ fontSize: isCenter ? 11 : 9 }}
                  >
                    {node.label}
                  </text>
                )}
                <title>
                  {node.kind === "center"
                    ? `전체 ${node.count}건`
                    : `${node.label} · ${node.count}건`}
                </title>
              </g>
            );
          })}
        </svg>

        {hoverId && nodeMap[hoverId] && nodeMap[hoverId].kind !== "center" && (
          <div className="border-border pointer-events-none absolute bottom-2 left-2 rounded-lg border bg-background/95 px-2.5 py-1.5 text-xs shadow-sm">
            <p className="font-medium">{nodeMap[hoverId].label}</p>
            <p className="text-muted-foreground tabular-nums">{nodeMap[hoverId].count}건</p>
          </div>
        )}
      </div>
    </div>
  );
}
