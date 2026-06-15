const MOCK_TOP_FIVE = [
  { rank: 1, label: "Synapse Core" },
  { rank: 2, label: "Navigator Path" },
  { rank: 3, label: "Trend Signal" },
  { rank: 4, label: "Index Cluster" },
  { rank: 5, label: "Archive Node" },
] as const;

export function TopFivePanel() {
  return (
    <div className="border-border absolute right-4 bottom-4 w-44 rounded-xl border bg-card/95 p-3 shadow-sm backdrop-blur-sm">
      <p className="text-muted-foreground mb-2 text-[10px] font-semibold tracking-widest uppercase">
        Top 5
      </p>
      <ol className="space-y-1.5">
        {MOCK_TOP_FIVE.map(({ rank, label }) => (
          <li
            key={rank}
            className="flex items-center gap-2 text-xs"
          >
            <span className="bg-accent text-accent-foreground flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold">
              {rank}
            </span>
            <span className="text-foreground truncate">{label}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
