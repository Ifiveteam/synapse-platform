import { AgentCard } from "@/components/agent-card";
import { AGENTS } from "@/lib/agents";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-16">
      <header className="mb-12 text-center">
        <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
          Synapse Platform
        </p>
        <h1 className="text-4xl font-bold tracking-tight">AI Agents</h1>
        <p className="text-muted-foreground mx-auto mt-4 max-w-xl text-base">
          실행할 에이전트를 선택하세요. 각 에이전트는 백엔드의 전문 모듈과
          연결됩니다.
        </p>
      </header>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {AGENTS.map((agent, index) => (
          <AgentCard key={agent.id} agent={agent} index={index + 1} />
        ))}
      </div>
    </main>
  );
}
