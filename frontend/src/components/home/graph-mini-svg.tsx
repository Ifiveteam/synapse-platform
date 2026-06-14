const NODES = [
  { cx: 200, cy: 140, r: 22, muted: true },
  { cx: 320, cy: 90, r: 16, muted: true },
  { cx: 380, cy: 200, r: 18, muted: true },
  { cx: 120, cy: 220, r: 14, muted: true },
  { cx: 280, cy: 260, r: 20, muted: true },
  { cx: 250, cy: 170, r: 28, muted: false },
] as const;

const EDGES: [number, number][] = [
  [0, 5],
  [1, 5],
  [2, 5],
  [3, 5],
  [4, 5],
  [0, 3],
  [1, 2],
];

export function GraphMiniSvg({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 480 320" className={className} aria-hidden>
      {EDGES.map(([a, b], i) => (
        <line
          key={i}
          x1={NODES[a].cx}
          y1={NODES[a].cy}
          x2={NODES[b].cx}
          y2={NODES[b].cy}
          stroke="var(--border)"
          strokeWidth={1.5}
        />
      ))}
      {NODES.map((node, i) => (
        <circle
          key={i}
          cx={node.cx}
          cy={node.cy}
          r={node.r}
          fill={node.muted ? "var(--graph-accent-muted)" : "var(--graph-accent)"}
          opacity={node.muted ? 0.55 : 1}
        />
      ))}
    </svg>
  );
}
