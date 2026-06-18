import { ScoreIntensityBar } from "@/components/analyses/score-intensity-bar";
import { temperamentBarData } from "@/lib/analyses/temperament";

interface TemperamentBarsProps {
  scores: Record<string, number>;
  className?: string;
}

export function TemperamentBars({ scores, className }: TemperamentBarsProps) {
  const items = temperamentBarData(scores);

  return (
    <div className={className}>
      <div className="mb-3">
        <p className="text-sm font-semibold">기질</p>
        <p className="text-muted-foreground text-xs">
          TCI 기질 · 시청에서 읽히는 성향 · 0=약함 · 100=강함
        </p>
      </div>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.key}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="text-foreground font-medium">{item.label}</span>
              <span
                className={`tabular-nums ${
                  item.value >= 55 ? "text-violet-700" : "text-muted-foreground"
                }`}
              >
                {item.value}
              </span>
            </div>
            <ScoreIntensityBar value={item.value} label={item.label} />
          </li>
        ))}
      </ul>
    </div>
  );
}
