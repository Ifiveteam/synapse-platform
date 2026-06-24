import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";

import type { AnalysisListItem } from "@/api/types/profiler";
import { InteractiveGraph } from "@/components/home/graph-mini-svg";
import { cn } from "@/lib/utils";

// ── Virtual canvas ─────────────────────────────────────────────────────────
const CANVAS_W = 3200;
const CANVAS_H = 1100;
const PLANET_R = 58;

const PLANET_COLORS = ["#6366f1", "#38bdf8", "#a78bfa", "#34d399", "#fb923c", "#f472b6"];

// Deterministic star field (LCG)
const STARS = Array.from({ length: 90 }, (_, i) => {
  const s = Math.imul(i * 1664525 + 1013904223, 1) >>> 0;
  return {
    x: (s % CANVAS_W),
    y: ((s >>> 12) % CANVAS_H),
    r: 0.5 + (s % 8) * 0.18,
    o: 0.12 + (s % 6) * 0.07,
  };
});

// ── Helpers ─────────────────────────────────────────────────────────────────
function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}

interface WorldDatum {
  id: string;
  dateLabel: string;
  ordinal: string;
  color: string;
  cx: number;
  cy: number;
}

function buildWorlds(items: AnalysisListItem[]): WorldDatum[] {
  const completed = items
    .filter((it) => it.status === "completed" && it.kind === "snapshot")
    .sort((a, b) => (a.snapshot_date ?? "").localeCompare(b.snapshot_date ?? ""));

  const total = completed.length;
  if (total === 0) return [];

  const gap = Math.min(700, CANVAS_W / (total + 0.8));
  const startX = CANVAS_W / 2 - (gap * (total - 1)) / 2;
  const yShifts = [0, -70, 55, -40, 80, -60];

  return completed.map((item, i) => ({
    id: item.id,
    dateLabel: formatDate(item.snapshot_date),
    ordinal: `${i + 1}지구`,
    color: PLANET_COLORS[i % PLANET_COLORS.length],
    cx: startX + i * gap,
    cy: CANVAS_H / 2 + yShifts[i % yShifts.length],
  }));
}

// ── Component ────────────────────────────────────────────────────────────────
interface Props {
  analyses: AnalysisListItem[];
}

export function MultiWorldGraph({ analyses }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [vp, setVp] = useState({ x: 0, y: 0, k: 1 });
  const [focused, setFocused] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const dragRef = useRef<{ sx: number; sy: number; tx: number; ty: number } | null>(null);
  const worlds = buildWorlds(analyses);

  // Fit all worlds on first render
  useEffect(() => {
    const el = containerRef.current;
    if (!el || worlds.length === 0) return;
    const { width, height } = el.getBoundingClientRect();
    const k = Math.min((width / CANVAS_W) * 0.9, (height / CANVAS_H) * 0.9, 1);
    const x = (width - CANVAS_W * k) / 2;
    const y = (height - CANVAS_H * k) / 2;
    setVp({ x, y, k });
    setReady(true);
  }, [worlds.length]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    setVp((prev) => {
      const factor = e.deltaY < 0 ? 1.13 : 0.88;
      const k = Math.max(0.1, Math.min(5, prev.k * factor));
      return {
        x: mx - (mx - prev.x) * (k / prev.k),
        y: my - (my - prev.y) * (k / prev.k),
        k,
      };
    });
  }, []);

  const onBgDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      dragRef.current = { sx: e.clientX, sy: e.clientY, tx: vp.x, ty: vp.y };
    },
    [vp.x, vp.y],
  );

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.sx;
    const dy = e.clientY - dragRef.current.sy;
    setVp((prev) => ({ ...prev, x: dragRef.current!.tx + dx, y: dragRef.current!.ty + dy }));
  }, []);

  const onMouseUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const zoomToWorld = useCallback((world: WorldDatum) => {
    const el = containerRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const targetK = 2.2;
    setVp({
      x: width / 2 - world.cx * targetK,
      y: height / 2 - world.cy * targetK,
      k: targetK,
    });
    setTimeout(() => setFocused(world.id), 280);
  }, []);

  const goBack = useCallback(() => {
    setFocused(null);
    const el = containerRef.current;
    if (!el || worlds.length === 0) return;
    const { width, height } = el.getBoundingClientRect();
    const k = Math.min((width / CANVAS_W) * 0.9, (height / CANVAS_H) * 0.9, 1);
    setVp({ x: (width - CANVAS_W * k) / 2, y: (height - CANVAS_H * k) / 2, k });
  }, [worlds.length]);

  if (focused) {
    return (
      <div className="relative h-full w-full">
        <button
          type="button"
          onClick={goBack}
          className="text-muted-foreground hover:text-foreground hover:bg-secondary absolute top-3 left-3 z-10 flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs transition-colors"
        >
          <ArrowLeft size={13} />
          전체 보기
        </button>
        <InteractiveGraph />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative h-full w-full overflow-hidden cursor-grab active:cursor-grabbing select-none",
        "transition-opacity duration-300",
        ready ? "opacity-100" : "opacity-0",
      )}
      onWheel={handleWheel}
      onMouseDown={onBgDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <svg width="100%" height="100%" aria-hidden>
        <defs>
          <filter id="mwg-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {worlds.map((w) => (
            <radialGradient key={w.id} id={`mwg-planet-${w.id}`} cx="35%" cy="28%" r="70%">
              <stop offset="0%" stopColor={w.color} stopOpacity="1" />
              <stop offset="55%" stopColor={w.color} stopOpacity="0.75" />
              <stop offset="100%" stopColor={w.color} stopOpacity="0.45" />
            </radialGradient>
          ))}
        </defs>

        <g transform={`translate(${vp.x},${vp.y}) scale(${vp.k})`}>
          {/* Star field */}
          {STARS.map((s, i) => (
            <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="currentColor" className="text-muted-foreground" opacity={s.o} />
          ))}

          {/* Dotted connection line */}
          {worlds.length > 1 &&
            worlds.map((w, i) => {
              if (i === 0) return null;
              const prev = worlds[i - 1];
              return (
                <line
                  key={`conn-${i}`}
                  x1={prev.cx}
                  y1={prev.cy}
                  x2={w.cx}
                  y2={w.cy}
                  stroke="currentColor"
                  className="text-border"
                  strokeWidth={1.2}
                  strokeDasharray="5 10"
                  opacity={0.35}
                />
              );
            })}

          {/* Planets */}
          {worlds.map((world) => (
            <g
              key={world.id}
              onClick={() => zoomToWorld(world)}
              className="cursor-pointer"
              role="button"
              aria-label={`${world.ordinal} ${world.dateLabel}`}
            >
              {/* Outer glow */}
              <circle
                cx={world.cx}
                cy={world.cy}
                r={PLANET_R + 16}
                fill={world.color}
                opacity={0.07}
                filter="url(#mwg-glow)"
              />

              {/* Orbit ring */}
              <ellipse
                cx={world.cx}
                cy={world.cy}
                rx={PLANET_R + 22}
                ry={(PLANET_R + 22) * 0.3}
                fill="none"
                stroke={world.color}
                strokeWidth={1.5}
                opacity={0.22}
              />

              {/* Planet body */}
              <circle
                cx={world.cx}
                cy={world.cy}
                r={PLANET_R}
                fill={`url(#mwg-planet-${world.id})`}
                className="transition-opacity duration-150 hover:opacity-85"
              />

              {/* Highlight shimmer */}
              <ellipse
                cx={world.cx - PLANET_R * 0.22}
                cy={world.cy - PLANET_R * 0.28}
                rx={PLANET_R * 0.28}
                ry={PLANET_R * 0.15}
                fill="white"
                opacity={0.18}
                style={{ pointerEvents: "none" }}
              />

              {/* Ordinal label (on planet) */}
              <text
                x={world.cx}
                y={world.cy + 6}
                textAnchor="middle"
                fontSize={15}
                fontWeight="700"
                fill="white"
                opacity={0.92}
                style={{ pointerEvents: "none", fontFamily: "Inter, -apple-system, sans-serif" }}
              >
                {world.ordinal}
              </text>

              {/* Date label (below planet) */}
              <text
                x={world.cx}
                y={world.cy + PLANET_R + 24}
                textAnchor="middle"
                fontSize={13}
                fontWeight="500"
                fill="currentColor"
                className="text-foreground"
                opacity={0.65}
                style={{ pointerEvents: "none", fontFamily: "Inter, -apple-system, sans-serif" }}
              >
                {world.dateLabel}
              </text>
            </g>
          ))}
        </g>
      </svg>

      <p className="pointer-events-none absolute bottom-4 left-4 text-[11px] text-muted-foreground opacity-50">
        스크롤로 줌 · 드래그로 이동 · 클릭으로 탐색
      </p>
    </div>
  );
}
