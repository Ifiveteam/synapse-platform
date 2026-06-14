import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, FlaskConical } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ROUTES } from "@/routes";

const DEMO_ROUTES = [
  { label: "Profiler", href: ROUTES.profiler },
  { label: "Navigator", href: ROUTES.navigator },
  { label: "Aggregator", href: ROUTES.agentDetail("aggregator") },
  { label: "Indexer", href: ROUTES.indexer },
  { label: "Archiver", href: ROUTES.agentDetail("archiver") },
] as const;

export function DemoMenu() {
  const [open, setOpen] = useState(false);
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

  return (
    <div ref={ref} className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="border-border text-muted-foreground hover:text-foreground gap-1.5"
        onClick={() => setOpen((v) => !v)}
      >
        <FlaskConical size={14} />
        시연 메뉴
        <ChevronDown
          size={14}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </Button>

      {open && (
        <div className="border-border absolute top-full right-0 z-50 mt-2 min-w-[168px] rounded-xl border bg-card py-1 shadow-lg">
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
        </div>
      )}
    </div>
  );
}
