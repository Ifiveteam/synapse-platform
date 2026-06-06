import { notFound } from "next/navigation";

import { AgentDetail } from "@/components/agent-detail";
import { AGENTS, getAgent } from "@/lib/agents";

interface AgentPageProps {
  params: Promise<{ slug: string }>;
}

export function generateStaticParams() {
  return AGENTS.map((agent) => ({ slug: agent.id }));
}

export async function generateMetadata({ params }: AgentPageProps) {
  const { slug } = await params;
  const agent = getAgent(slug);

  if (!agent) {
    return { title: "Agent Not Found" };
  }

  return {
    title: `${agent.name} | Synapse Platform`,
    description: agent.description,
  };
}

export default async function AgentPage({ params }: AgentPageProps) {
  const { slug } = await params;
  const agent = getAgent(slug);

  if (!agent) {
    notFound();
  }

  const index = AGENTS.findIndex((item) => item.id === agent.id) + 1;

  return <AgentDetail agent={agent} index={index} />;
}
