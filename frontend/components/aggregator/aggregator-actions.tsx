import Link from "next/link";

import { AggregatorAnalyzeButton } from "@/components/aggregator/aggregator-analyze-button";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/lib/routes";

interface AggregatorActionsProps {
  agentSlug: string;
}

export function AggregatorActions({ agentSlug }: AggregatorActionsProps) {
  return (
    <div className="space-y-3">
      <AggregatorAnalyzeButton agentSlug={agentSlug} />
      <Button asChild variant="outline" size="lg" className="w-full">
        <Link href={ROUTES.trendPosts(agentSlug)}>발행된 리포트 목록 보기</Link>
      </Button>
    </div>
  );
}
