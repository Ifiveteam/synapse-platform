import { Bookmark, MessageSquare, Search, Target, TrendingUp, Zap } from "lucide-react";

const W = 320;
const H = 140;
const CX = W / 2;
const CY = H / 2;
const RADIUS = 52;
const CENTER_R = 24;
const NODE_R = 16;

const OUTER_NODES = [
  { label: "트렌드",  color: "#60a5fa", icon: TrendingUp   },
  { label: "분석",    color: "#818cf8", icon: Search        },
  { label: "스크랩",  color: "#38bdf8", icon: Bookmark      },
  { label: "채팅",    color: "#a78bfa", icon: MessageSquare },
  { label: "이상향",  color: "#c084fc", icon: Target        },
].map((n, i) => {
  const angle = (i / 5) * Math.PI * 2 - Math.PI / 2;
  return { ...n, x: CX + Math.cos(angle) * RADIUS, y: CY + Math.sin(angle) * RADIUS };
});

export function PentagonGraph() {
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-hidden>
      {/* 오각형 엣지 */}
      {OUTER_NODES.map((node, i) => (
        <line
          key={`edge-center-${i}`}
          x1={CX} y1={CY}
          x2={node.x} y2={node.y}
          stroke="var(--border)"
          strokeWidth={1.2}
          strokeLinecap="round"
        />
      ))}
      {OUTER_NODES.map((node, i) => {
        const next = OUTER_NODES[(i + 1) % 5];
        return (
          <line
            key={`edge-outer-${i}`}
            x1={node.x} y1={node.y}
            x2={next.x} y2={next.y}
            stroke="var(--border)"
            strokeWidth={1}
            strokeLinecap="round"
            strokeOpacity={0.5}
          />
        );
      })}

      {/* 외부 노드 */}
      {OUTER_NODES.map((node, i) => {
        const Icon = node.icon;
        const fo = NODE_R * 1.6;
        return (
          <g key={i}>
            <circle cx={node.x} cy={node.y} r={NODE_R} fill={node.color} opacity={0.9} />
            <foreignObject
              x={node.x - fo / 2}
              y={node.y - fo / 2}
              width={fo}
              height={fo}
              style={{ pointerEvents: "none" }}
            >
              <div style={{ width: fo, height: fo, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icon size={NODE_R * 0.85} color="white" />
              </div>
            </foreignObject>
          </g>
        );
      })}

      {/* 중앙 Synapse 노드 */}
      <circle cx={CX} cy={CY} r={CENTER_R} fill="#6366f1" />
      <foreignObject
        x={CX - CENTER_R}
        y={CY - CENTER_R}
        width={CENTER_R * 2}
        height={CENTER_R * 2}
        style={{ pointerEvents: "none" }}
      >
        <div style={{ width: CENTER_R * 2, height: CENTER_R * 2, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Zap size={CENTER_R * 0.9} color="white" />
        </div>
      </foreignObject>
    </svg>
  );
}
