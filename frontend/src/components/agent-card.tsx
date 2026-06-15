import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Agent, AgentStatus } from "@/lib/agents";
import { ROUTES } from "@/routes";
import { useAgentSelection } from "@/stores/shell";

interface AgentCardProps {
  agent: Agent;
  index: number;
}

const STATUS_BADGE: Record<
  AgentStatus,
  { label: string; className: string }
> = {
  stable:  { label: "운영 중",  className: "bg-emerald-100 text-emerald-700" },
  dev:     { label: "개발 중",  className: "bg-amber-100  text-amber-700"   },
  planned: { label: "예정",     className: "bg-gray-100   text-gray-500"    },
};

export function AgentCard({ agent, index }: AgentCardProps) {
  const setSelectedAgentId = useAgentSelection(
    (state) => state.setSelectedAgentId,
  );
  const badge = STATUS_BADGE[agent.status];
  const isDev     = agent.status === "dev";
  const isPlanned = agent.status === "planned";

  return (
    <Card
      className={`relative transition-shadow hover:shadow-md ${
        isDev ? "border-amber-200" : isPlanned ? "opacity-60" : ""
      }`}
    >
      {/* 상태 뱃지 */}
      <span
        className={`absolute right-3 top-3 rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.className}`}
      >
        {agent.statusLabel ?? badge.label}
      </span>

      <CardHeader className="pr-20">
        <CardTitle className="flex items-center gap-2">
          <span className="text-muted-foreground text-sm font-normal">
            Agent {index}
          </span>
          {agent.name}
        </CardTitle>
        <CardDescription>{agent.description}</CardDescription>
      </CardHeader>

      <CardContent>
        {isPlanned ? (
          <Button disabled className="w-full" size="lg" variant="outline">
            준비 중
          </Button>
        ) : (
          <Button
            asChild
            className={`w-full ${isDev ? "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100" : ""}`}
            size="lg"
            variant={isDev ? "outline" : "default"}
          >
            <Link
              to={ROUTES.agentDetail(agent.id)}
              onClick={() => setSelectedAgentId(agent.id)}
            >
              {agent.name} 열기
              {isDev && (
                <span className="ml-1.5 text-[10px] font-normal opacity-70">
                  (임시)
                </span>
              )}
            </Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
