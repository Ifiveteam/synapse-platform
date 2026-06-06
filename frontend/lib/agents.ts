export type AgentId =
  | "aggregator"
  | "archiver"
  | "indexer"
  | "navigator"
  | "profiler";

export interface Agent {
  id: AgentId;
  name: string;
  description: string;
}

export const AGENTS: Agent[] = [
  {
    id: "aggregator",
    name: "Aggregator",
    description: "여러 소스의 데이터를 수집하고 통합합니다.",
  },
  {
    id: "archiver",
    name: "Archiver",
    description: "데이터를 아카이브하고 장기 보관을 관리합니다.",
  },
  {
    id: "indexer",
    name: "Indexer",
    description: "콘텐츠를 인덱싱하여 빠른 검색을 지원합니다.",
  },
  {
    id: "navigator",
    name: "Navigator",
    description: "정보 탐색과 경로 안내를 수행합니다.",
  },
  {
    id: "profiler",
    name: "Profiler",
    description: "프로파일링과 성능 분석을 담당합니다.",
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
