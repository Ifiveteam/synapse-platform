import { HomeHeader } from "@/components/home/home-header";
import { HomeTrendBriefing } from "@/components/home/home-trend-briefing";

export function HomePage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <HomeHeader />
      <HomeTrendBriefing />
    </div>
  );
}
