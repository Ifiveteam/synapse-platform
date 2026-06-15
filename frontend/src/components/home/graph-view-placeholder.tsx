import { GraphMiniSvg } from "@/components/home/graph-mini-svg";

export function GraphViewPlaceholder() {
  return (
    <div className="relative flex h-full min-h-[320px] flex-col">
      <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
        Graph View
      </p>

      <div className="border-border relative flex flex-1 items-center justify-center overflow-hidden rounded-xl border bg-card">
        <GraphMiniSvg className="h-full w-full max-h-full max-w-full" />

        <p className="text-muted-foreground pointer-events-none absolute bottom-4 left-4 text-xs">
          프로파일 데이터 연결 후 실제 그래프가 표시됩니다.
        </p>
      </div>
    </div>
  );
}
