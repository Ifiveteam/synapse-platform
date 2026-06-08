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
    description: "수많은 디지털 자아들을 모아 트렌드를 읽어내는 시장 분석가",
  },
  {
    id: "archiver",
    name: "Archiver",
    description: "사용자가 의도적으로 수집한 지식을 내재화하고 함께 토론하는 지적 동반자",
  },
  {
    id: "indexer",
    name: "Indexer",
    description: "사용자의 무의식적인 디지털 발자국을 빠짐없이 기록하고 정돈하는 기억 저장소",
  },
  {
    id: "navigator",
    name: "Navigator",
    description: "사용자가 원하는 이상향으로 나아갈 수 있도록 이끄는 페이스메이커",
  },
  {
    id: "profiler",
    name: "Profiler",
    description: "데이터라는 거울을 통해 사용자의 현재 상태와 성향을 있는 그대로 비춰주는 분석가",
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
