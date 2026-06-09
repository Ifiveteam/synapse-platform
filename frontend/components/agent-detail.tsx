"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Agent } from "@/lib/agents";
import { ROUTES } from "@/lib/routes";
import { useAgentSelection } from "@/stores/shell/agent-selection";

interface AgentDetailProps {
  agent: Agent;
  index: number;
}

export function AgentDetail({ agent, index }: AgentDetailProps) {
  const selectedAgentId = useAgentSelection((state) => state.selectedAgentId);
  const setSelectedAgentId = useAgentSelection(
    (state) => state.setSelectedAgentId,
  );

  useEffect(() => {
    setSelectedAgentId(agent.id);
  }, [agent.id, setSelectedAgentId]);

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-16">
      <Button asChild variant="ghost" className="mb-8 w-fit">
        <Link href={ROUTES.home}>
          <ArrowLeft className="size-4" />
          메인으로 돌아가기
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <p className="text-muted-foreground text-sm font-medium">
            Agent {index}
          </p>
          <CardTitle className="text-3xl">{agent.name}</CardTitle>
          <CardDescription className="text-base">
            {agent.description}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted rounded-lg p-4 text-sm">
            <p>
              <span className="text-muted-foreground">에이전트 ID:</span>{" "}
              <code className="font-mono">{agent.id}</code>
            </p>
            {selectedAgentId === agent.id && (
              <p className="text-muted-foreground mt-2">
                Zustand 스토어에 현재 에이전트가 선택되었습니다.
              </p>
            )}
          </div>
          <p className="text-muted-foreground text-sm">
            이 화면에서 {agent.name} 에이전트와의 상호작용 UI를 확장할 수
            있습니다.
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
