export type AgentId =
  | "aggregator"
  | "archiver"
  | "indexer"
  | "navigator"
  | "profiler";

export type AgentStatus = "stable" | "dev" | "planned";

export interface Agent {
  id: AgentId;
  name: string;
  description: string;
  status: AgentStatus;
  statusLabel?: string;
}

export const AGENTS: Agent[] = [
  {
    id: "aggregator",
    name: "Aggregator",
    description: "여러 소스의 데이터를 수집하고 통합합니다.",
    status: "planned",
  },
  {
    id: "archiver",
    name: "Archiver",
    description: "데이터를 아카이브하고 장기 보관을 관리합니다.",
    status: "planned",
  },
  {
    id: "indexer",
    name: "Indexer",
    description: "콘텐츠를 인덱싱하여 빠른 검색을 지원합니다.",
    status: "planned",
  },
  {
    id: "navigator",
    name: "Navigator",
    description: "이상향 설계 및 버블 탈출 행동 유도 에이전트.",
    status: "dev",
    statusLabel: "개발 중",
  },
  {
    id: "profiler",
    name: "Profiler",
    description: "YouTube 소비 패턴을 8각 레이더 차트로 분석합니다.",
    status: "planned",
  },
];

export const AGENT_MAP = Object.fromEntries(
  AGENTS.map((agent) => [agent.id, agent]),
) as Record<AgentId, Agent>;

export function isAgentId(value: string): value is AgentId {
  return value in AGENT_MAP;
}

export function getAgent(id: string): Agent | undefined {
  if (!isAgentId(id)) return undefined;
  return AGENT_MAP[id];
}
