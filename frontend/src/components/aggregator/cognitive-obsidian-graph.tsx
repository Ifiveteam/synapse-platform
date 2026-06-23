import { useMemo, useState } from "react";

import type { CognitiveAxisScore } from "@/api/trend";
import { cn } from "@/lib/utils";

export interface CognitiveObsidianGraphProps {
  radarChartData: CognitiveAxisScore[];
  dominantAxes?: string[];
  deficientAxes?: string[];
  cohortSize?: number;
  className?: string;
}

interface GraphNode extends CognitiveAxisScore {
  x: number;
  y: number;
  labelX: number;
  labelY: number;
  angle: number;
  nodeRadius: number;
  role: "dominant" | "deficient" | "neutral";
}

const VIEW_SIZE = 100;
const CENTER = 50;
const MAX_RADIUS = 30;
const LABEL_RADIUS = 42;

const COLORS = {
  bg: "#0b0f17",
  ring: "rgba(99, 102, 241, 0.22)",
  edge: "rgba(129, 140, 248, 0.35)",
  spoke: "rgba(99, 102, 241, 0.15)",
  label: "rgba(203, 213, 225, 0.8)",
  dominant: "#4ade80",
  dominantGlow: "rgba(74, 222, 128, 0.5)",
  deficient: "#f87171",
  deficientGlow: "rgba(248, 113, 113, 0.45)",
  neutral: "#818cf8",
} as const;

function polarToCartesian(angle: number, radius: number) {
  return {
    x: CENTER + radius * Math.cos(angle),
    y: CENTER - radius * Math.sin(angle),
  };
}

function matchesAxisName(subject: string, candidates: string[]): boolean {
  const normalized = subject.trim().toLowerCase();
  return candidates.some(
    (name) =>
      name.trim().toLowerCase() === normalized ||
      normalized.includes(name.trim().toLowerCase()) ||
      name.trim().toLowerCase().includes(normalized),
  );
}

function buildNodes(
  data: CognitiveAxisScore[],
  dominantAxes: string[],
  deficientAxes: string[],
): GraphNode[] {
  if (data.length === 0) return [];

  const count = data.length;
  const maxScore = Math.max(...data.map((d) => d.score));
  const minScore = Math.min(...data.map((d) => d.score));

  return data.map((axis, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
    const radius = (axis.score / 100) * MAX_RADIUS;
    const { x, y } = polarToCartesian(angle, radius);
    const label = polarToCartesian(angle, LABEL_RADIUS);

    const isDominant =
      matchesAxisName(axis.subject, dominantAxes) || axis.score === maxScore;
    const isDeficient =
      matchesAxisName(axis.subject, deficientAxes) || axis.score === minScore;

    let role: GraphNode["role"] = "neutral";
    if (isDominant && !isDeficient) role = "dominant";
    else if (isDeficient && !isDominant) role = "deficient";
    else if (isDominant) role = "dominant";

    return {
      ...axis,
      x,
      y,
      labelX: label.x,
      labelY: label.y,
      angle,
      nodeRadius: 1.1 + (axis.score / 100) * 1.8,
      role,
    };
  });
}

function nodeFill(node: GraphNode): string {
  if (node.role === "dominant") return COLORS.dominant;
  if (node.role === "deficient") return COLORS.deficient;
  return COLORS.neutral;
}

function nodeOpacity(node: GraphNode, hoveredKey: string | null): number {
  if (!hoveredKey) return 0.5 + (node.score / 100) * 0.5;
  if (hoveredKey === node.key) return 1;
  return 0.2;
}

interface TooltipCardProps {
  node: GraphNode;
  left: string;
  top: string;
}

function TooltipCard({ node, left, top }: TooltipCardProps) {
  return (
    <div
      className="pointer-events-none absolute z-20 max-w-[220px] rounded-lg border border-indigo-500/30 bg-slate-900/95 px-3 py-2 shadow-xl shadow-indigo-950/40 backdrop-blur-sm"
      style={{ left, top, transform: "translate(-50%, -115%)" }}
    >
      <p className="text-xs font-semibold text-indigo-200">
        {node.subject}: {node.score.toFixed(1)}
      </p>
      <p className="mt-1 rounded-md bg-indigo-950/60 px-2 py-1 text-[11px] leading-snug text-slate-300">
        {node.interpretation}
      </p>
    </div>
  );
}

export function CognitiveObsidianGraph({
  radarChartData,
  dominantAxes = [],
  deficientAxes = [],
  cohortSize,
  className,
}: CognitiveObsidianGraphProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  const nodes = useMemo(
    () => buildNodes(radarChartData, dominantAxes, deficientAxes),
    [radarChartData, dominantAxes, deficientAxes],
  );

  const hoveredNode = nodes.find((node) => node.key === hoveredKey) ?? null;

  const dominantLabel =
    dominantAxes[0] ??
    nodes.reduce((best, node) => (node.score > best.score ? node : best), nodes[0])
      ?.subject ??
    "—";

  const deficientLabel =
    deficientAxes[0] ??
    nodes.reduce((worst, node) => (node.score < worst.score ? node : worst), nodes[0])
      ?.subject ??
    "—";

  const rings = [0.25, 0.5, 0.75, 1];

  return (
    <div className={cn("flex w-full flex-col gap-3", className)}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">8각 인지 성향 균형도</h3>
        {cohortSize !== undefined && (
          <p className="text-muted-foreground text-xs">
            분석 대상 {cohortSize.toLocaleString("ko-KR")}명
          </p>
        )}
      </div>

      <div
        className="relative h-[400px] w-full overflow-hidden rounded-xl border border-slate-800 bg-[#0b0f17] shadow-inner sm:h-[440px]"
        onMouseLeave={() => setHoveredKey(null)}
      >
        <svg
          viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
          className="h-full w-full"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="8각 인지 성향 옵시디언 그래프"
        >
          <rect
            x={0}
            y={0}
            width={VIEW_SIZE}
            height={VIEW_SIZE}
            fill={COLORS.bg}
          />

          {rings.map((ratio) => (
            <circle
              key={ratio}
              cx={CENTER}
              cy={CENTER}
              r={MAX_RADIUS * ratio}
              fill="none"
              stroke={COLORS.ring}
              strokeWidth={0.2}
              strokeDasharray="1.2 1.8"
            />
          ))}

          {nodes.map((node) => (
            <line
              key={`spoke-${node.key}`}
              x1={CENTER}
              y1={CENTER}
              x2={node.x}
              y2={node.y}
              stroke={COLORS.spoke}
              strokeWidth={0.18}
            />
          ))}

          {nodes.map((node, index) => {
            const next = nodes[(index + 1) % nodes.length];
            const dimmed =
              hoveredKey &&
              hoveredKey !== node.key &&
              hoveredKey !== next.key;
            return (
              <line
                key={`edge-${node.key}-${next.key}`}
                x1={node.x}
                y1={node.y}
                x2={next.x}
                y2={next.y}
                stroke={COLORS.edge}
                strokeWidth={0.22}
                strokeOpacity={dimmed ? 0.12 : 0.55}
              />
            );
          })}

          {nodes.map((node, index) => {
            const opposite = nodes[(index + nodes.length / 2) % nodes.length];
            return (
              <line
                key={`cross-${node.key}-${opposite.key}`}
                x1={node.x}
                y1={node.y}
                x2={opposite.x}
                y2={opposite.y}
                stroke={COLORS.edge}
                strokeWidth={0.15}
                strokeOpacity={0.14}
              />
            );
          })}

          {nodes.map((node) => (
            <text
              key={`label-${node.key}`}
              x={node.labelX}
              y={node.labelY}
              textAnchor="middle"
              dominantBaseline="central"
              fill={COLORS.label}
              fontSize={2.4}
              fontWeight={500}
              opacity={
                hoveredKey && hoveredKey !== node.key ? 0.3 : 0.9
              }
            >
              {node.subject}
            </text>
          ))}

          {nodes.map((node) => {
            const isHovered = hoveredKey === node.key;
            const fill = nodeFill(node);
            const opacity = nodeOpacity(node, hoveredKey);
            const glow =
              node.role === "dominant"
                ? COLORS.dominantGlow
                : node.role === "deficient"
                  ? COLORS.deficientGlow
                  : "rgba(129, 140, 248, 0.35)";

            return (
              <g
                key={`node-${node.key}`}
                onMouseEnter={() => setHoveredKey(node.key)}
                style={{ cursor: "pointer" }}
              >
                {(isHovered || node.role !== "neutral") && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.nodeRadius + 1.2}
                    fill={glow}
                    opacity={isHovered ? 0.95 : 0.4}
                  />
                )}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.nodeRadius}
                  fill={fill}
                  fillOpacity={opacity}
                  stroke={isHovered ? "#e2e8f0" : fill}
                  strokeWidth={isHovered ? 0.35 : 0.15}
                  strokeOpacity={isHovered ? 1 : 0.7}
                />
              </g>
            );
          })}
        </svg>

        {hoveredNode && (
          <TooltipCard
            node={hoveredNode}
            left={`${hoveredNode.x}%`}
            top={`${hoveredNode.y}%`}
          />
        )}

        <div className="pointer-events-none absolute bottom-4 left-4 z-10 max-w-[72%] space-y-1.5">
          <p className="text-base font-bold tracking-tight text-emerald-400 sm:text-lg">
            🔥 우세 성향 축
            <span className="mt-0.5 block text-lg font-semibold text-emerald-300 sm:text-xl">
              {dominantLabel}
            </span>
          </p>
          <p className="text-[11px] text-slate-500 sm:text-xs">
            <span className="text-rose-400/90">⚠️ 저조 성향 축</span>{" "}
            <span className="text-slate-400">{deficientLabel}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
