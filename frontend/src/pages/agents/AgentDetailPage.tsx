import { useParams, Navigate } from "react-router-dom";

import { AggregatorActions } from "@/components/aggregator/aggregator-actions";
import { AgentDetail } from "@/components/agent-detail";
import { AGENTS, getAgent } from "@/lib/agents";
import { ROUTES } from "@/routes";

const SLUG_AGENTS = AGENTS.filter((agent) => agent.id !== "profiler");

export function AgentDetailPage() {
  const { slug = "" } = useParams();

  if (slug === "profiler") {
    return <Navigate to={ROUTES.profiler} replace />;
  }

  const agent = getAgent(slug);
  if (!agent) {
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
