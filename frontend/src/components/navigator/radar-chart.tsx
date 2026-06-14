import { AXIS_LABELS, AXIS_TYPES, AXIS_TYPE_COLOR } from "@/lib/navigator/types";
import type { AxisKey, IdealRadarChart, RadarChart } from "@/lib/navigator/types";

// ── 8축 순서 (위에서 시계방향) ──
const AXES: AxisKey[] = [
  "intellectual_curiosity",  // 0 — 상단 (북)
  "self_improvement",        // 1 — 우상 (북동)
  "social_awareness",        // 2 — 우 (동)
  "depth_immersion",         // 3 — 우하 (남동)
  "practical_orientation",   // 4 — 하 (남)
  "emotional_comfort",       // 5 — 좌하 (남서)
  "creative_expression",     // 6 — 좌 (서)
  "entertainment_release",   // 7 — 좌상 (북서)
];

const CX = 180;
const CY = 180;
const R  = 130;   // 최대 반지름 (점수 100 기준)
const RINGS = [20, 40, 60, 80, 100];
const LABEL_OFFSET = 22;

function angleOf(i: number) {
  // 0번 축 = 북쪽(-90도), 시계방향
  return (i * 45 - 90) * (Math.PI / 180);
}

function point(score: number, i: number) {
  const a = angleOf(i);
  const r = (score / 100) * R;
  return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) };
}

function polygon(scores: number[]) {
  return scores.map((s, i) => {
    const p = point(s, i);
    return `${p.x},${p.y}`;
  }).join(" ");
}

function labelPos(i: number) {
  const a = angleOf(i);
  const r = R + LABEL_OFFSET;
  return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) };
}

function textAnchor(i: number): "middle" | "start" | "end" {
  const x = Math.cos(angleOf(i));
  if (x > 0.3) return "start";
  if (x < -0.3) return "end";
  return "middle";
}

interface RadarChartProps {
  current: RadarChart;
  ideal?:  IdealRadarChart | null;
  size?:   number;
  showLegend?: boolean;
}

export function NavigatorRadarChart({
  current,
  ideal,
  size = 360,
  showLegend = true,
}: RadarChartProps) {
  const currentScores  = AXES.map((k) => current[k] as number);
  const idealScores    = ideal ? AXES.map((k) => ideal[k] as number) : null;

  const vb = `0 0 ${CX * 2} ${CY * 2}`;

  return (
    <div className="flex flex-col items-center gap-3">
      <svg
        viewBox={vb}
        width={size}
        height={size}
        aria-label="8각 레이더 차트"
      >
        {/* ── 배경 링 ── */}
        {RINGS.map((r) => {
          const pts = AXES.map((_, i) => {
            const a = angleOf(i);
            const rr = (r / 100) * R;
            return `${CX + rr * Math.cos(a)},${CY + rr * Math.sin(a)}`;
          }).join(" ");
          return (
            <polygon
              key={r}
              points={pts}
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="1"
            />
          );
        })}

        {/* ── 링 점수 라벨 (20, 60, 100) ── */}
        {[20, 60, 100].map((r) => (
          <text
            key={r}
            x={CX + 3}
            y={CY - (r / 100) * R + 4}
            fontSize="8"
            fill="#9ca3af"
          >
            {r}
          </text>
        ))}

        {/* ── 축 선 ── */}
        {AXES.map((_, i) => {
          const p = point(100, i);
          return (
            <line
              key={i}
              x1={CX} y1={CY}
              x2={p.x} y2={p.y}
              stroke="#e5e7eb"
              strokeWidth="1"
            />
          );
        })}

        {/* ── 이상향 영역 (뒤에 렌더) ── */}
        {idealScores && (
          <polygon
            points={polygon(idealScores)}
            fill="rgba(239,68,68,0.10)"
            stroke="#ef4444"
            strokeWidth="1.5"
            strokeDasharray="5 3"
          />
        )}

        {/* ── 현재 영역 ── */}
        <polygon
          points={polygon(currentScores)}
          fill="rgba(59,130,246,0.15)"
          stroke="#3b82f6"
          strokeWidth="2"
        />

        {/* ── 현재 점 ── */}
        {currentScores.map((s, i) => {
          const p = point(s, i);
          return (
            <circle key={i} cx={p.x} cy={p.y} r="4" fill="#3b82f6" />
          );
        })}

        {/* ── 이상향 점 ── */}
        {idealScores?.map((s, i) => {
          const p = point(s, i);
          return (
            <circle key={i} cx={p.x} cy={p.y} r="3.5" fill="#ef4444" stroke="#fff" strokeWidth="1" />
          );
        })}

        {/* ── 축 라벨 ── */}
        {AXES.map((key, i) => {
          const lp  = labelPos(i);
          const ta  = textAnchor(i);
          const type = AXIS_TYPES[key];
          const colorMap: Record<string, string> = {
            GROWTH:    "#059669",
            EXPANSION: "#7c3aed",
            FLEXIBLE:  "#d97706",
          };
          const score = currentScores[i];
          return (
            <g key={key}>
              <text
                x={lp.x}
                y={lp.y - 4}
                textAnchor={ta}
                fontSize="10"
                fontWeight="600"
                fill={colorMap[type]}
              >
                {AXIS_LABELS[key]}
              </text>
              <text
                x={lp.x}
                y={lp.y + 8}
                textAnchor={ta}
                fontSize="9"
                fill="#6b7280"
              >
                {score}
              </text>
            </g>
          );
        })}
      </svg>

      {/* ── 범례 ── */}
      {showLegend && (
        <div className="flex items-center gap-6 text-xs text-gray-500">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-5 bg-blue-500 rounded" />
            현재 프로필
          </span>
          {ideal && (
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block h-0.5 w-5 rounded"
                style={{
                  background: "repeating-linear-gradient(90deg,#ef4444 0,#ef4444 5px,transparent 5px,transparent 8px)",
                }}
              />
              이상향
            </span>
          )}
          <span className={`flex items-center gap-1 ${AXIS_TYPE_COLOR.GROWTH}`}>● 성장축</span>
          <span className={`flex items-center gap-1 ${AXIS_TYPE_COLOR.EXPANSION}`}>● 확장축</span>
          <span className={`flex items-center gap-1 ${AXIS_TYPE_COLOR.FLEXIBLE}`}>● 유연축</span>
        </div>
      )}
    </div>
  );
}
