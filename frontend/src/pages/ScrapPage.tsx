import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bookmark, ChevronDown, LayoutGrid, List, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  SCRAP_GRAPH_EDGES,
  SCRAP_GRAPH_NODES,
  SCRAP_LIST_ITEMS,
  type ScrapFilterMode,
  type ScrapGraphNode,
  type ScrapViewMode,
} from "@/lib/scraps/mock";
import { ROUTES } from "@/routes";
import { cn } from "@/lib/utils";

const FILTER_TABS: { id: ScrapFilterMode; label: string }[] = [
  { id: "all", label: "전체보기" },
  { id: "category", label: "카테고리별" },
  { id: "date", label: "날짜별" },
];

function ScrapGraphView({
  selectedId,
  onSelect,
  onOpenDetail,
}: {
  selectedId: string | null;
  onSelect: (node: ScrapGraphNode | null) => void;
  onOpenDetail: (scrapId: string) => void;
}) {
  const nodeMap = useMemo(
    () => Object.fromEntries(SCRAP_GRAPH_NODES.map((n) => [n.id, n])),
    [],
  );

  return (
    <div className="border-border relative min-h-[420px] flex-1 overflow-hidden rounded-2xl border bg-card">
      <svg
        viewBox="0 0 800 480"
        className="h-full w-full"
        role="img"
        aria-label="스크랩 키워드 그래프"
      >
        {SCRAP_GRAPH_EDGES.map(([a, b], i) => {
          const from = nodeMap[a];
          const to = nodeMap[b];
          if (!from || !to) return null;
          return (
            <line
              key={i}
              x1={from.cx}
              y1={from.cy}
              x2={to.cx}
              y2={to.cy}
              stroke="var(--border)"
              strokeWidth={1.5}
            />
          );
        })}

        {SCRAP_GRAPH_NODES.map((node) => (
          <g
            key={node.id}
            className="cursor-pointer"
            onClick={() => {
              if (node.isCenter) {
                onSelect(selectedId === node.id ? null : node);
                return;
              }
              if (node.scrapId) {
                onOpenDetail(node.scrapId);
                return;
              }
              onSelect(selectedId === node.id ? null : node);
            }}
          >
            <circle
              cx={node.cx}
              cy={node.cy}
              r={node.r}
              fill={node.fill}
              opacity={selectedId && selectedId !== node.id ? 0.45 : 0.9}
              stroke={selectedId === node.id ? "var(--primary)" : "transparent"}
              strokeWidth={3}
            />
            <text
              x={node.cx}
              y={node.cy + 4}
              textAnchor="middle"
              className="fill-white text-[11px] font-semibold select-none"
              style={{ fontSize: node.isCenter ? 13 : 11 }}
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>

      {selectedId && nodeMap[selectedId] && !nodeMap[selectedId].isCenter && (
        <NodePopup
          node={nodeMap[selectedId]}
          onClose={() => onSelect(null)}
          onOpenDetail={onOpenDetail}
        />
      )}
    </div>
  );
}

function NodePopup({
  node,
  onClose,
  onOpenDetail,
}: {
  node: ScrapGraphNode;
  onClose: () => void;
  onOpenDetail: (scrapId: string) => void;
}) {
  const left = `${(node.cx / 800) * 100}%`;
  const top = `${(node.cy / 480) * 100}%`;

  return (
    <div
      className="border-border absolute z-10 w-52 -translate-x-1/2 -translate-y-[110%] rounded-xl border bg-card p-3 shadow-lg"
      style={{ left, top }}
    >
      <p className="text-sm font-semibold">{node.label}</p>
      <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">
        {node.summary}
      </p>
      <div className="mt-3 flex gap-2">
        {node.scrapId ? (
          <Button
            size="sm"
            variant="outline"
            className="h-8 flex-1 gap-1 text-xs"
            onClick={() => onOpenDetail(node.scrapId!)}
          >
            <Bookmark size={12} />
            상세보기
          </Button>
        ) : (
          <Button size="sm" variant="outline" className="h-8 flex-1 gap-1 text-xs">
            <Bookmark size={12} />
            스크랩
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          className="text-destructive h-8 flex-1 gap-1 text-xs"
          onClick={onClose}
        >
          <Trash2 size={12} />
          삭제
        </Button>
      </div>
    </div>
  );
}

function ScrapListView() {
  return (
    <div className="flex flex-col gap-3">
      {SCRAP_LIST_ITEMS.map((item) => (
        <Link
          key={item.id}
          to={ROUTES.scrapDetail(item.id)}
          className="border-border hover:bg-secondary/50 flex items-center gap-4 rounded-2xl border bg-card px-4 py-4 transition-colors"
        >
          <div className="bg-accent text-accent-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
            <Bookmark size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{item.title}</p>
            <p className="text-muted-foreground mt-0.5 text-xs">
              {item.category} · {item.savedAt}
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}

export function ScrapPage() {
  const navigate = useNavigate();
  const [view, setView] = useState<ScrapViewMode>("graph");
  const [filter, setFilter] = useState<ScrapFilterMode>("all");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const openDetail = (scrapId: string) => {
    navigate(ROUTES.scrapDetail(scrapId));
  };

  return (
    <div className="flex h-full min-h-0 flex-col px-6 py-6">
      <div className="mb-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <h1 className="text-xl font-semibold tracking-tight">
          스크랩 — 비슷한 키워드
        </h1>

        <div className="flex flex-wrap items-center gap-2">
          <Tabs
            value={filter}
            onValueChange={(v) => setFilter(v as ScrapFilterMode)}
            className="gap-0"
          >
            <TabsList className="h-9 bg-transparent p-0">
              {FILTER_TABS.map(({ id, label }) => (
                <TabsTrigger
                  key={id}
                  value={id}
                  className="rounded-full px-3 text-xs shadow-none"
                >
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <Button variant="outline" size="sm" className="gap-1 text-xs">
            필터
            <ChevronDown size={14} />
          </Button>

          <div className="border-border ml-1 flex rounded-full border p-0.5">
            <button
              type="button"
              onClick={() => setView("list")}
              className={cn(
                "flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                view === "list"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <List size={14} />
              리스트
            </button>
            <button
              type="button"
              onClick={() => setView("graph")}
              className={cn(
                "flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                view === "graph"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <LayoutGrid size={14} />
              그래프
            </button>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        {view === "graph" ? (
          <ScrapGraphView
            selectedId={selectedNodeId}
            onSelect={(node) => setSelectedNodeId(node?.id ?? null)}
            onOpenDetail={openDetail}
          />
        ) : (
          <ScrapListView />
        )}
      </div>
    </div>
  );
}
