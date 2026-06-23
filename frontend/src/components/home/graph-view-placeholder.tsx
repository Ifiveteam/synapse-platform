import { useEffect, useMemo, useRef, useState } from "react";

import { fetchEmbeddingGraph, type EmbeddingGraphData, type EmbeddingGraphNode } from "@/api/indexer";
import { listMyAnalyses } from "@/api/profiler";
import type { AnalysisListItem } from "@/api/types/profiler";
import { EmbeddingCatalogGraph } from "@/components/analyses/embedding-catalog-graph";
import { EmbeddingCatalogGraph3DView } from "@/components/analyses/embedding-catalog-graph-3d";
import { DualGlobeCanvas } from "@/components/home/dual-globe-canvas";
import { InteractiveGraph } from "@/components/home/graph-mini-svg";
import { useAuthStore } from "@/stores/auth";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}

// ── 3D 상세 뷰 (구체 클릭 후) ──────────────────────────────────────────────

interface GlobeDetailViewProps {
  data: EmbeddingGraphData;
  label: string;
  onBack: () => void;
}

function GlobeDetailView({ data, label, onBack }: GlobeDetailViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 400 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r) setSize({ w: Math.floor(r.width), h: Math.floor(r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const nodeById = useMemo<Map<string, EmbeddingGraphNode>>(
    () => new Map(data.nodes.map((n) => [n.id, n])),
    [data.nodes],
  );

  return (
    <div ref={containerRef} className="relative h-full w-full">
      {/* 뒤로가기 버튼 */}
      <button
        onClick={onBack}
        className="absolute left-3 top-3 z-20 flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-[11px] font-medium text-white/80 backdrop-blur-sm transition hover:bg-black/80 hover:text-white"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M7.5 2L3.5 6L7.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        돌아가기
      </button>

      {/* 레이블 */}
      <div className="pointer-events-none absolute left-1/2 top-3 z-20 -translate-x-1/2">
        <span className="rounded-full bg-black/50 px-3 py-1 text-[11px] font-semibold text-white/70 backdrop-blur-sm">
          {label}
        </span>
      </div>

      <EmbeddingCatalogGraph3DView
        data={data}
        categoryFilter={null}
        nodeById={nodeById}
        width={size.w}
        height={size.h}
      />
    </div>
  );
}

// ── 멀티 구체 뷰 (최대 5개) ─────────────────────────────────────────────────

interface DualGlobeViewProps {
  analyses: AnalysisListItem[];
}

function DualGlobeView({ analyses }: DualGlobeViewProps) {
  const sorted = useMemo(
    () =>
      [...analyses]
        .sort((a, b) => (a.snapshot_date ?? "").localeCompare(b.snapshot_date ?? ""))
        .slice(0, 5),
    [analyses],
  );

  const [globes, setGlobes] = useState<(EmbeddingGraphData | null)[]>([]);
  const [selected, setSelected] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 400 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r) setSize({ w: Math.floor(r.width), h: Math.floor(r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const fetches = sorted.map((item, i) => {
      const isLast = i === sorted.length - 1;
      return (
        isLast
          ? fetchEmbeddingGraph()
          : fetchEmbeddingGraph({ before: item.snapshot_date ?? undefined })
      )
        .then((d) => (d.total > 0 ? d : null))
        .catch(() => null);
    });
    Promise.all(fetches).then(setGlobes);
  }, [sorted]);

  const pairs = useMemo(
    () =>
      sorted
        .map((item, i) => ({ data: globes[i] ?? null, label: formatDate(item.snapshot_date) }))
        .filter((p): p is { data: EmbeddingGraphData; label: string } => p.data !== null),
    [sorted, globes],
  );

  const globeData = useMemo(() => pairs.map((p) => p.data), [pairs]);
  const globeLabels = useMemo(() => pairs.map((p) => p.label), [pairs]);

  // 구체 클릭 → 3D 상세 뷰
  if (selected !== null && pairs[selected]) {
    return (
      <div ref={containerRef} className="relative h-full w-full">
        <GlobeDetailView
          data={pairs[selected].data}
          label={pairs[selected].label}
          onBack={() => setSelected(null)}
        />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative h-full w-full">
      {globeData.length > 0 ? (
        <DualGlobeCanvas
          data={globeData}
          labels={globeLabels}
          width={size.w}
          height={size.h}
          onGlobeClick={setSelected}
        />
      ) : (
        <div className="flex h-full items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}
    </div>
  );
}

// ── 최상위 컴포넌트 ─────────────────────────────────────────────────────────

export function GraphViewPlaceholder() {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);
  const [graph, setGraph] = useState<EmbeddingGraphData | null | "empty">(null);
  const [analyses, setAnalyses] = useState<AnalysisListItem[] | null>(null);

  useEffect(() => {
    if (!user || !token) return;
    fetchEmbeddingGraph()
      .then((data) => setGraph(data.total > 0 ? data : "empty"))
      .catch(() => setGraph("empty"));
    listMyAnalyses().then(setAnalyses);
  }, [user, token]);

  const completed =
    analyses?.filter((a) => a.status === "completed" && a.kind === "snapshot") ?? [];

  if (completed.length >= 2) {
    return (
      <div className="relative flex h-full min-h-[320px] flex-col">
        <div className="border-border relative flex flex-1 overflow-hidden rounded-xl border bg-card">
          <DualGlobeView analyses={completed} />
        </div>
      </div>
    );
  }

  if (graph && graph !== "empty") {
    return (
      <div className="relative flex h-full min-h-[320px] flex-col">
        <EmbeddingCatalogGraph data={graph} className="flex-1" hideControls />
      </div>
    );
  }

  return (
    <div className="relative flex h-full min-h-[320px] flex-col">
      <div className="border-border relative flex flex-1 overflow-hidden rounded-xl border bg-card">
        <InteractiveGraph />
        <p className="text-muted-foreground pointer-events-none absolute bottom-4 left-4 text-xs">
          시청 데이터 분석 후 실제 그래프가 표시됩니다.
        </p>
      </div>
    </div>
  );
}
