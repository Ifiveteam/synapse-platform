interface Axis {
  key: string;
  label: string;
}

interface Props {
  title: string;
  subtitle?: string;
  axes: readonly Axis[];
  current: Record<string, number>;
  ideal: Record<string, number>;
}

function clamp(v: number | undefined): number {
  return Math.round(Math.max(0, Math.min(100, v ?? 0)));
}

/**
 * 한 그룹(가치관/기질)의 축들을 현재 vs 이상향으로 비교.
 * 막대(muted) = 현재, 세로 틱(primary) = 이상향 목표.
 */
export function CompareBars({ title, subtitle, axes, current, ideal }: Props) {
  return (
    <div>
      <div className="mb-3">
        <p className="text-sm font-semibold">{title}</p>
        {subtitle && (
          <p className="text-muted-foreground text-xs">{subtitle}</p>
        )}
      </div>
      <ul className="space-y-2.5">
        {axes.map((a) => {
          const c = clamp(current[a.key]);
          const i = clamp(ideal[a.key]);
          return (
            <li key={a.key}>
              <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
                <span className="text-foreground font-medium">{a.label}</span>
                <span className="tabular-nums">
                  <span className="text-muted-foreground">{c}</span>
                  <span className="text-muted-foreground"> → </span>
                  <span className="text-primary font-medium">{i}</span>
                </span>
              </div>
              <div className="bg-secondary relative h-2 rounded-full">
                <div
                  className="bg-muted-foreground/50 absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${c}%` }}
                />
                <div
                  className="bg-primary absolute top-1/2 h-3.5 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{ left: `${i}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
