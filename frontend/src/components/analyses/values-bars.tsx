import { ScoreIntensityBar } from "@/components/analyses/score-intensity-bar";
import { valuesBarData } from "@/lib/analyses/values";

interface ValuesBarsProps {
  scores: Record<string, number>;
  className?: string;
}

export function ValuesBars({ scores, className }: ValuesBarsProps) {
  const items = valuesBarData(scores);

  return (
    <div className={className}>
      <div className="mb-4">
        <p className="text-sm font-semibold">가치관</p>
        <p className="text-muted-foreground text-xs">
          0=관심 없음 · 100=강하게 추구
        </p>
      </div>
      <ul className="grid grid-cols-2 gap-x-2 gap-y-3 sm:grid-cols-5 sm:gap-x-3">
        {items.map((item) => (
          <li key={item.key} className="flex min-w-0 flex-col gap-1.5">
            <span className="text-foreground truncate text-center text-[11px] font-medium leading-tight">
              {item.label}
            </span>
            <ScoreIntensityBar value={item.value} label={item.label} heightClass="h-1.5" />
            <span
              className={`text-center text-[10px] tabular-nums ${
                item.value >= 55 ? "text-violet-700" : "text-muted-foreground"
              }`}
            >
              {item.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
