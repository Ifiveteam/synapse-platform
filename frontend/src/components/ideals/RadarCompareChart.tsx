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
  /** current(기준) 선 색 — 지정 시 인라인 색, 미지정 시 muted-foreground 테마색. */
  currentColor?: string;
  /** ideal(비교) 선 색 — 지정 시 인라인 색, 미지정 시 primary 테마색. */
  idealColor?: string;
  /** 점선으로 그릴 축 — 기본은 "ideal"(비교). "current"면 기준을 점선으로. */
  dashed?: "current" | "ideal";
}

function polar(cx: number, cy: number, radius: number, angle: number, value: number) {
  const r = (Math.max(0, Math.min(100, value)) / 100) * radius;
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)] as const;
}

/**
 * 현재 vs 이상향 8축 스파이더(레이더) 비교 차트.
 * 색은 shadcn 테마 토큰을 따른다 — 현재=muted-foreground, 이상향=primary.
 */
export function RadarCompareChart({
  axes,
  size = 300,
  labelMargin = 52,
  currentColor,
  idealColor,
  dashed = "ideal",
}: Props) {
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

      {/* 현재(기준) */}
      <polygon
        points={toPoints("current")}
        className={
          currentColor ? undefined : "fill-muted-foreground/10 stroke-muted-foreground"
        }
        style={
          currentColor
            ? { fill: `${currentColor}1a`, stroke: currentColor }
            : undefined
        }
        strokeWidth={2}
        strokeDasharray={dashed === "current" ? "5 3" : undefined}
      />
      {/* 이상향(비교) */}
      <polygon
        points={toPoints("ideal")}
        className={idealColor ? undefined : "fill-primary/10 stroke-primary"}
        style={
          idealColor ? { fill: `${idealColor}1a`, stroke: idealColor } : undefined
        }
        strokeWidth={2}
        strokeDasharray={dashed === "ideal" ? "5 3" : undefined}
      />
    </svg>
  );
}
