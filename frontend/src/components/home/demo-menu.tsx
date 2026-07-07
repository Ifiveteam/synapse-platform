import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, FlaskConical, Loader2, Play } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ROUTES } from "@/routes";
import { triggerAggregatorBatch } from "@/services/aggregator";

const DEMO_ROUTES = [
  { label: "Archiver", href: ROUTES.agentDetail("archiver") },
  { label: "트렌드 대시보드", href: ROUTES.reporterTrendGraph },
] as const;

export function DemoMenu() {
  const [open, setOpen] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const handleTriggerAggregator = async () => {
    if (triggering) return;
    setTriggering(true);
    try {
      const result = await triggerAggregatorBatch();
      toast.success(
        `${result.message} · 집계 완료 후 트렌드 대시보드에서 [실시간 분석 실행]을 눌러주세요.`,
      );
      setOpen(false);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Aggregator 배치 실행에 실패했습니다.";
      toast.error(message);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div ref={ref} className="relative">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-muted-foreground hover:text-foreground h-7 gap-1.5 px-2.5 text-xs"
        onClick={() => setOpen((v) => !v)}
      >
        <FlaskConical size={13} />
        시연
        <ChevronDown
          size={12}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </Button>

      {open && (
        <div className="border-border absolute top-full right-0 z-50 mt-2 min-w-[208px] rounded-xl border bg-card py-1 shadow-lg">
          {DEMO_ROUTES.map(({ label, href }) => (
            <Link
              key={href}
              to={href}
              onClick={() => setOpen(false)}
              className="text-foreground hover:bg-accent block px-3 py-2 text-sm transition-colors"
            >
              시연 · {label}
            </Link>
          ))}

          <div className="border-border my-1 border-t" />

          <button
            type="button"
            onClick={() => void handleTriggerAggregator()}
            disabled={triggering}
            className="text-foreground hover:bg-accent flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          >
            {triggering ? (
              <Loader2 size={13} className="shrink-0 animate-spin" />
            ) : (
              <Play size={13} className="shrink-0" />
            )}
            Aggregator 배치 실행
          </button>
        </div>
      )}
    </div>
  );
}
