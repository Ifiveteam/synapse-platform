import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, TrendingUp, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  MOCK_HOT_NEWS,
  MOCK_TOP_KEYWORDS_OVERLAY,
  MOCK_TOP_OPINIONS,
  MOCK_TREND_INDEX_POINTS,
} from "@/lib/trends/mock";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";

function MiniTrendChart() {
  const points = MOCK_TREND_INDEX_POINTS;
  const w = 280;
  const h = 80;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const coords = points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((v - min) / (max - min || 1)) * (h - 8) - 4;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-20 w-full" aria-hidden>
      <polyline
        points={coords}
        fill="none"
        stroke="var(--graph-accent)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TopFiveList({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <div className="min-w-0 flex-1">
      <p className="text-muted-foreground mb-2 text-[10px] font-semibold tracking-widest uppercase">
        {title}
      </p>
      <ol className="space-y-1.5">
        {items.map((label, i) => (
          <li key={label} className="flex items-center gap-2 text-xs">
            <span className="bg-accent text-accent-foreground flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold">
              {i + 1}
            </span>
            <span className="truncate">{label}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function TrendHoverOverlay() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dismissedRef = useRef(false);

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = setTimeout(() => {
      setOpen(false);
      dismissedRef.current = false;
    }, 200);
  };

  const handleOpen = () => {
    if (dismissedRef.current) return;
    cancelClose();
    setOpen(true);
  };

  const handleDismiss = () => {
    dismissedRef.current = true;
    cancelClose();
    setOpen(false);
  };

  return (
    <>
      {/* 오른쪽 아래 호버 트리거 */}
      <div
        className="absolute bottom-0 right-0 z-20 h-20 w-20"
        onMouseEnter={handleOpen}
        onMouseLeave={scheduleClose}
        aria-hidden
      />
      <div
        className="absolute bottom-4 right-0 z-20 flex w-5 h-14 cursor-pointer items-center justify-center"
        onMouseEnter={handleOpen}
        onMouseLeave={scheduleClose}
      >
        <div className="bg-primary h-10 w-1.5 rounded-l-full opacity-80" />
      </div>

      {/* 패널 — 오른쪽 아래에서 올라옴 */}
      <aside
        className={cn(
          "border-border absolute bottom-2 right-2 z-30 flex w-[min(360px,88%)] max-h-[90%] flex-col overflow-hidden rounded-2xl border bg-card/98 shadow-2xl backdrop-blur-sm transition-all duration-200 ease-out",
          open ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-4 opacity-0",
        )}
        onMouseEnter={handleOpen}
        onMouseLeave={scheduleClose}
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <TrendingUp size={15} className="text-primary" />
            <span className="text-sm font-semibold">트렌드</span>
          </div>
          <button
            type="button"
            onClick={handleDismiss}
            className="text-muted-foreground hover:bg-secondary rounded-lg p-1.5 transition-colors"
            aria-label="닫기"
          >
            <X size={14} />
          </button>
        </div>

        <div className="flex min-h-0 flex-col gap-4 overflow-y-auto p-4">
          <div className="border-border rounded-xl border bg-secondary/30 px-4 py-4">
            <p className="text-muted-foreground text-[10px] font-semibold tracking-widest uppercase">
              {MOCK_HOT_NEWS.title}
            </p>
            <p className="mt-2 text-sm leading-snug font-medium">
              {MOCK_HOT_NEWS.headline}
            </p>
          </div>

          <div className="flex gap-4">
            <TopFiveList title="Top 5 오피니언" items={MOCK_TOP_OPINIONS} />
            <TopFiveList title="Top 5 키워드" items={MOCK_TOP_KEYWORDS_OVERLAY} />
          </div>

          <div>
            <p className="text-muted-foreground mb-2 text-[10px] font-semibold tracking-widest uppercase">
              트렌드 지수
            </p>
            <div className="border-border rounded-xl border bg-card px-3 py-2">
              <MiniTrendChart />
            </div>
          </div>
        </div>

        <div className="border-t p-3">
          <Button className="w-full gap-2" size="sm" onClick={() => navigate(ROUTES.trends)}>
            더보기
            <ArrowRight size={14} />
          </Button>
        </div>
      </aside>
    </>
  );
}
