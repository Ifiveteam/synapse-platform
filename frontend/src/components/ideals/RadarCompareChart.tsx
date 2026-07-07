export interface RadarAxis {
  label: string;
  current: number;
  ideal: number;
}

interface Props {
  axes: RadarAxis[];
  size?: number;
  /** 라벨용 바깥 여백(px). 작게 줄이면 다각형이 커진다 (라벨은 overflow-visible로 표시). */
  labelMargin?: number;
}

function polar(cx: number, cy: number, radius: number, angle: number, value: number) {
  const r = (Math.max(0, Math.min(100, value)) / 100) * radius;
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)] as const;
}

/**
 * 현재 vs 이상향 8축 스파이더(레이더) 비교 차트.
 * 색은 shadcn 테마 토큰을 따른다 — 현재=muted-foreground, 이상향=primary.
 */
export function RadarCompareChart({ axes, size = 300, labelMargin = 52 }: Props) {
  const n = axes.length;
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - labelMargin; // 라벨 여백 (작을수록 다각형이 큼)
  const rings = [25, 50, 75, 100];

  const angleAt = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n;

  const toPoints = (key: "current" | "ideal") =>
    axes
      .map((a, i) => polar(cx, cy, radius, angleAt(i), a[key]).join(","))
      .join(" ");

  // 그리드 octagon(값 레벨별)
  const ringPolygon = (level: number) =>
    axes
      .map((_, i) => polar(cx, cy, radius, angleAt(i), level).join(","))
      .join(" ");

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="overflow-visible"
    >
      {/* 그리드 링 */}
      {rings.map((lvl) => (
        <polygon
          key={lvl}
          points={ringPolygon(lvl)}
          fill="none"
          className="stroke-border"
          strokeWidth={1}
        />
      ))}

      {/* 축 스포크 + 라벨 */}
      {axes.map((a, i) => {
        const angle = angleAt(i);
        const [ex, ey] = polar(cx, cy, radius, angle, 100);
        const [lx, ly] = polar(cx, cy, radius + 18, angle, 100);
        const dx = Math.cos(angle);
        const anchor = dx > 0.2 ? "start" : dx < -0.2 ? "end" : "middle";
        return (
          <g key={a.label}>
            <line
              x1={cx}
              y1={cy}
              x2={ex}
              y2={ey}
              className="stroke-border"
              strokeWidth={1}
            />
            <text
              x={lx}
              y={ly}
              className="fill-muted-foreground"
              fontSize={11}
              textAnchor={anchor}
              dominantBaseline="middle"
            >
              {a.label}
            </text>
          </g>
        );
      })}

      {/* 현재 */}
      <polygon
        points={toPoints("current")}
        className="fill-muted-foreground/10 stroke-muted-foreground"
        strokeWidth={2}
      />
      {/* 이상향 */}
      <polygon
        points={toPoints("ideal")}
        className="fill-primary/10 stroke-primary"
        strokeWidth={2}
        strokeDasharray="5 3"
      />
    </svg>
  );
}
