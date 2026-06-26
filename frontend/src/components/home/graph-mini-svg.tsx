import * as d3 from "d3-force";
import { Bookmark, MessageSquare, Search, Target, TrendingUp, Zap } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ComponentType } from "react";

interface NodePopup {
  nodeId: number;
  x: number;
  y: number;
}

const NODE_DETAILS: Record<number, { title: string; content: React.ReactNode }> = {
  0: {
    title: "트렌드",
    content: (
      <ul className="space-y-1.5 text-xs">
        {["AI 반도체 공급망", "전기차 배터리 기술", "바이오헬스 투자"].map((t, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-indigo-400">#{i + 1}</span>
            <span>{t}</span>
          </li>
        ))}
      </ul>
    ),
  },
  1: {
    title: "분석",
    content: (
      <div className="text-xs space-y-1">
        <p className="text-muted-foreground">최근 분석 영상</p>
        <p className="font-medium truncate">2024 AI 트렌드 총정리</p>
        <p className="font-medium truncate">반도체 산업 전망 리포트</p>
      </div>
    ),
  },
  2: {
    title: "스크랩",
    content: (
      <div className="text-xs space-y-1">
        <p className="text-muted-foreground">저장된 스크랩 12개</p>
        <p className="font-medium truncate">📌 GPT-5 발표 정리</p>
        <p className="font-medium truncate">📌 퀀텀컴퓨팅 입문</p>
      </div>
    ),
  },
  3: {
    title: "채팅",
    content: (
      <div className="text-xs space-y-1">
        <p className="text-muted-foreground">최근 대화</p>
        <p className="font-medium truncate">AI 투자 전략에 대해...</p>
        <p className="font-medium truncate">반도체 공부 방법은?</p>
      </div>
    ),
  },
  4: {
    title: "이상향",
    content: (
      <div className="text-xs space-y-2">
        <p className="text-muted-foreground">현재 이상향</p>
        <p className="font-semibold text-purple-400">테크 인사이터</p>
        <p className="text-[10px] text-muted-foreground">AI·반도체·투자 분야</p>
      </div>
    ),
  },
  5: {
    title: "Synapse",
    content: (
      <div className="text-xs space-y-1 text-center">
        <p className="text-muted-foreground">오케스트레이터</p>
        <p className="font-medium">모든 에이전트를 연결하고</p>
        <p className="font-medium">인사이트를 생성합니다</p>
      </div>
    ),
  },
};

interface NodeDatum extends d3.SimulationNodeDatum {
  id: number;
  label: string;
  color: string;
  r: number;
  icon: ComponentType<{ size?: number; color?: string }>;
}

interface LinkDatum extends d3.SimulationLinkDatum<NodeDatum> {
  source: number;
  target: number;
}

const NODES: NodeDatum[] = [
  { id: 0, label: "트렌드",  color: "#60a5fa", r: 22, icon: TrendingUp  },
  { id: 1, label: "분석",    color: "#818cf8", r: 18, icon: Search       },
  { id: 2, label: "스크랩",  color: "#38bdf8", r: 20, icon: Bookmark     },
  { id: 3, label: "채팅",    color: "#a78bfa", r: 17, icon: MessageSquare},
  { id: 4, label: "이상향",  color: "#c084fc", r: 20, icon: Target       },
  { id: 5, label: "Synapse", color: "#6366f1", r: 30, icon: Zap          },
];

const LINKS: LinkDatum[] = [
  { source: 0, target: 5 },
  { source: 1, target: 5 },
  { source: 2, target: 5 },
  { source: 3, target: 5 },
  { source: 4, target: 5 },
  { source: 0, target: 3 },
  { source: 1, target: 2 },
];

// 페이지 이동 후 돌아와도 위치 유지
let _persistedNodes: NodeDatum[] | null = null;
let _persistedLinks: LinkDatum[] | null = null;

export function InteractiveGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simRef = useRef<d3.Simulation<NodeDatum, LinkDatum> | null>(null);
  const [, forceUpdate] = useState(0);
  const nodesRef = useRef<NodeDatum[]>(_persistedNodes ?? NODES.map((n) => ({ ...n })));
  const linksRef = useRef<LinkDatum[]>(_persistedLinks ?? LINKS.map((l) => ({ ...l })));
  const dragNodeRef = useRef<NodeDatum | null>(null);
  const [popup, setPopup] = useState<NodePopup | null>(null);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const W = el.clientWidth || 600;
    const H = el.clientHeight || 400;

    if (!_persistedNodes) {
      nodesRef.current.forEach((n, i) => {
        n.x = W / 2 + Math.cos((i / NODES.length) * Math.PI * 2) * 110;
        n.y = H / 2 + Math.sin((i / NODES.length) * Math.PI * 2) * 110;
      });
    }

    const sim = d3
      .forceSimulation<NodeDatum>(nodesRef.current)
      .force("link", d3.forceLink<NodeDatum, LinkDatum>(linksRef.current)
        .id((d) => d.id)
        .distance(130)
        .strength(0.35),
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(W / 2, H / 2).strength(0.08))
      .force("collision", d3.forceCollide<NodeDatum>((d) => d.r + 14))
      .alphaDecay(0.025)
      .on("tick", () => forceUpdate((n) => n + 1));

    simRef.current = sim;
    return () => {
      sim.stop();
      _persistedNodes = nodesRef.current;
      _persistedLinks = linksRef.current;
    };
  }, []);

  const getSvgXY = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }, []);

  const onMouseDown = useCallback((node: NodeDatum, e: React.MouseEvent) => {
    e.preventDefault();
    dragNodeRef.current = node;
    node.fx = node.x;
    node.fy = node.y;
    simRef.current?.alphaTarget(0.3).restart();
  }, []);

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragNodeRef.current) return;
    const pos = getSvgXY(e.clientX, e.clientY);
    dragNodeRef.current.fx = pos.x;
    dragNodeRef.current.fy = pos.y;
  }, [getSvgXY]);

  const onMouseUp = useCallback(() => {
    if (!dragNodeRef.current) return;
    dragNodeRef.current.fx = null;
    dragNodeRef.current.fy = null;
    simRef.current?.alphaTarget(0);
    dragNodeRef.current = null;
  }, []);

  const onTouchStart = useCallback((node: NodeDatum, e: React.TouchEvent) => {
    const touch = e.touches[0];
    dragNodeRef.current = node;
    node.fx = node.x;
    node.fy = node.y;
    simRef.current?.alphaTarget(0.3).restart();
    const pos = getSvgXY(touch.clientX, touch.clientY);
    node.fx = pos.x;
    node.fy = pos.y;
  }, [getSvgXY]);

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (!dragNodeRef.current) return;
    e.preventDefault();
    const touch = e.touches[0];
    const pos = getSvgXY(touch.clientX, touch.clientY);
    dragNodeRef.current.fx = pos.x;
    dragNodeRef.current.fy = pos.y;
  }, [getSvgXY]);

  const onTouchEnd = useCallback(() => {
    if (!dragNodeRef.current) return;
    dragNodeRef.current.fx = null;
    dragNodeRef.current.fy = null;
    simRef.current?.alphaTarget(0);
    dragNodeRef.current = null;
  }, []);

  const closeDelayRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelClose = useCallback(() => {
    if (closeDelayRef.current) clearTimeout(closeDelayRef.current);
  }, []);

  const scheduleClose = useCallback(() => {
    cancelClose();
    closeDelayRef.current = setTimeout(() => setPopup(null), 200);
  }, [cancelClose]);

  const onNodeMouseEnter = useCallback((node: NodeDatum) => {
    cancelClose();
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    hoverTimerRef.current = setTimeout(() => {
      setPopup({ nodeId: node.id, x: node.x ?? 0, y: node.y ?? 0 });
    }, 1000);
  }, [cancelClose]);

  const onNodeMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    scheduleClose();
  }, [scheduleClose]);

  const nodes = nodesRef.current;
  // d3 forceLink가 시뮬레이션 시 source/target을 노드 객체로 치환(mutate)하므로 안전
  const links = linksRef.current as unknown as Array<{
    source: NodeDatum;
    target: NodeDatum;
  }>;

  return (
    <div ref={containerRef} className="relative h-full w-full">
      {/* 노드 상세 팝업 */}
      {popup && (() => {
        const detail = NODE_DETAILS[popup.nodeId];
        const node = nodes[popup.nodeId];
        const el = containerRef.current;
        if (!el || !detail) return null;
        const pxX = (node.x ?? 0);
        const pxY = (node.y ?? 0);
        const popupW = 180;
        const left = Math.min(Math.max(pxX - popupW / 2, 8), el.clientWidth - popupW - 8);
        const top = pxY - node.r - 110;
        return (
          <div
            className="border-border bg-card absolute z-50 rounded-xl border p-3 shadow-xl"
            style={{ left, top: Math.max(top, 8), width: popupW }}
            onMouseEnter={cancelClose}
            onMouseLeave={scheduleClose}
          >
            <p className="mb-2 text-xs font-semibold" style={{ color: node.color }}>{detail.title}</p>
            {detail.content}
          </div>
        );
      })()}

      <svg
        ref={svgRef}
        className="h-full w-full cursor-default select-none overflow-visible"
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        aria-hidden
      >
        <defs>
          {NODES.map((n) => (
            <radialGradient key={n.id} id={`grad-${n.id}`} cx="38%" cy="32%" r="65%">
              <stop offset="0%"   stopColor={n.color} stopOpacity="1" />
              <stop offset="100%" stopColor={n.color} stopOpacity="0.75" />
            </radialGradient>
          ))}
        </defs>

        {/* 엣지 */}
        {links.map((link, i) => {
          const s = link.source as NodeDatum;
          const t = link.target as NodeDatum;
          if (s.x == null || t.x == null) return null;
          return (
            <line
              key={i}
              x1={s.x} y1={s.y}
              x2={t.x} y2={t.y}
              stroke="var(--border)"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeOpacity={0.7}
            />
          );
        })}

        {/* 노드 */}
        {nodes.map((node) => {
          if (node.x == null) return null;
          const Icon = node.icon;
          const iconSize = node.r * 0.9;
          const foSize = iconSize * 2;

          return (
            <g
              key={node.id}
              transform={`translate(${node.x},${node.y})`}
              onMouseDown={(e) => onMouseDown(node, e)}
              onTouchStart={(e) => onTouchStart(node, e)}
              onMouseEnter={() => onNodeMouseEnter(node)}
              onMouseLeave={onNodeMouseLeave}
              className="cursor-grab active:cursor-grabbing"
            >
              {/* 본체 */}
              <circle r={node.r} fill={`url(#grad-${node.id})`} />
              {/* 아이콘 */}
              <foreignObject
                x={-foSize / 2}
                y={-foSize / 2}
                width={foSize}
                height={foSize}
                style={{ pointerEvents: "none" }}
              >
                <div
                  style={{
                    width: foSize,
                    height: foSize,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Icon size={iconSize} color="white" />
                </div>
              </foreignObject>

              {/* 라벨 */}
              <text
                y={node.r + 15}
                textAnchor="middle"
                fontSize={11}
                fill="var(--muted-foreground)"
                fontWeight="500"
                style={{
                  pointerEvents: "none",
                  fontFamily: "Inter, -apple-system, sans-serif",
                  letterSpacing: "-0.01em",
                }}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
