import { HomeHeader } from "@/components/home/home-header";
import { TrendGraphDashboard } from "@/pages/reporter/TrendGraphDashboard";

export function HomePage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <HomeHeader />
      <TrendGraphDashboard />
    </div>
  );
}
