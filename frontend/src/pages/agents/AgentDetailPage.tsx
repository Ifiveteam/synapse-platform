import { useParams, Navigate } from "react-router-dom";

import { AggregatorActions } from "@/components/aggregator/aggregator-actions";
import { AgentDetail } from "@/components/agent-detail";
import { AGENTS, getAgent } from "@/lib/agents";
import { ROUTES } from "@/routes";

// 시연용 단독 페이지(profiler/indexer/navigator)는 제거됨 — 제네릭 상세는 aggregator/archiver만.
const DETAIL_SLUGS = new Set<string>(["aggregator", "archiver"]);
const SLUG_AGENTS = AGENTS.filter((agent) => DETAIL_SLUGS.has(agent.id));

export function AgentDetailPage() {
  const { slug = "" } = useParams();

  const agent = getAgent(slug);
  if (!agent || !DETAIL_SLUGS.has(slug)) {
    return <Navigate to={ROUTES.home} replace />;
  }

  const index = SLUG_AGENTS.findIndex((item) => item.id === agent.id) + 1;

  return (
    <AgentDetail
      agent={agent}
      index={index}
      action={
        slug === "aggregator" ? (
          <AggregatorActions agentSlug={slug} />
        ) : undefined
      }
    />
  );
}
