"use client";

import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Agent } from "@/lib/agents";
import { ROUTES } from "@/lib/routes";
import { useAgentStore } from "@/stores/use-agent-store";

interface AgentCardProps {
  agent: Agent;
  index: number;
}

export function AgentCard({ agent, index }: AgentCardProps) {
  const setSelectedAgentId = useAgentStore((state) => state.setSelectedAgentId);

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-muted-foreground text-sm font-normal">
            Agent {index}
          </span>
          {agent.name}
        </CardTitle>
        <CardDescription>{agent.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild className="w-full" size="lg">
          <Link
            href={ROUTES.agentDetail(agent.id)}
            onClick={() => setSelectedAgentId(agent.id)}
          >
            {agent.name} 열기
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
