/** 0~100 단극 막대 (0=무관심, 100=강한 추구) */

interface ScoreIntensityBarProps {
  value: number;
  label: string;
  heightClass?: string;
}

export function ScoreIntensityBar({
  value,
  label,
  heightClass = "h-2",
}: ScoreIntensityBarProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div
      className={`bg-muted relative w-full overflow-hidden rounded-full ${heightClass}`}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped}
    >
      <div
        className="absolute top-0 left-0 h-full rounded-full bg-violet-500/75 transition-[width]"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
