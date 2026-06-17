export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface DbProfileResponse {
  user_id: string;
  snapshot_id: string;
  snapshot_date: string;
  scores: Record<string, number>;
  summary_text: string;
  persona_label: string | null;
  behavior_reasoning: string | null;
  dominant_traits: string[] | null;
  supporting_evidence: Record<string, unknown> | null;
  tone_of_user: string | null;
}

export interface Synapse8Axes {
  intellectual_curiosity: number;
  practical_orientation: number;
  emotional_comfort: number;
  social_awareness: number;
  creative_expression: number;
  entertainment_release: number;
  self_improvement: number;
  depth_immersion: number;
}

export interface LayerB {
  search_active_ratio: number;
  viewing_concentration: number;
  taste_diversity_index: number;
  exploration_depth: number;
}

export interface Top5Interest {
  rank: number;
  label: string;
  score: number;
  evidence: string[];
}

export interface ProfileInterpretation {
  consumption_mode: string;
  primary_lever: string;
  sovereignty_verdict: string;
  radar_gap_insight: string;
}

export interface BehaviorPatterns {
  hour_distribution: Record<string, number>;
  weekend_ratio: number;
  top_repeated_channels: Array<{ channel: string; count: number }>;
  top_repeated_tags: Array<{ tag: string; count: number }>;
}

export interface ProfilerResult {
  user_id: string;
  computed_at: string;
  axes: Synapse8Axes;
  layer_b: LayerB;
  top5_interests: Top5Interest[];
  summary: string;
  interpretation: ProfileInterpretation;
  axis_notes: Record<string, string>;
  investigation_log: string[];
  llm_used: boolean;
  behavior_patterns: BehaviorPatterns | null;
}

export interface InAppChannel {
  delivered: boolean;
}

export interface EmailChannel {
  attempted: boolean;
  sent: boolean;
  from_address: string;
  recipient_masked: string;
  error: string | null;
}

export interface NotificationChannels {
  in_app: InAppChannel;
  email: EmailChannel;
}

export interface NotificationPayload {
  type: string;
  message: string;
  channels: NotificationChannels;
}

export interface JobResponse {
  job_id: string;
  user_id: string;
  status: JobStatus;
  current_step: string | null;
  created_at: string;
  updated_at: string;
  result: ProfilerResult | null;
  error: string | null;
  notification: NotificationPayload | null;
}

export interface PersonaInfo {
  id: string;
  label: string;
  description: string;
}

export interface PersonasResponse {
  personas: PersonaInfo[];
}

export interface AnalyzeResponse {
  job_id: string;
  status: JobStatus;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  weight: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  relation: string;
  directed?: boolean;
}

export interface GraphViewData {
  kind: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AxesDelta {
  intellectual_curiosity: number;
  practical_orientation: number;
  emotional_comfort: number;
  social_awareness: number;
  creative_expression: number;
  entertainment_release: number;
  self_improvement: number;
  depth_immersion: number;
}

export interface LayerBDelta {
  search_active_ratio: number;
  viewing_concentration: number;
  taste_diversity_index: number;
  exploration_depth: number;
}

export interface ProfileCompareDelta {
  user_id: string;
  from_version: string;
  to_version: string;
  axes_delta: AxesDelta;
  layer_b_delta: LayerBDelta;
  top5_added: string[];
  top5_removed: string[];
}

export interface AnomalyItem {
  code: string;
  message: string;
  severity: string;
}

export interface CompareResponse {
  delta: ProfileCompareDelta;
  anomalies: AnomalyItem[];
}

export interface SnapshotListResponse {
  user_id: string;
  versions: string[];
}

export const SYNAPSE_AXIS_KEYS = [
  "intellectual_curiosity",
  "practical_orientation",
  "emotional_comfort",
  "social_awareness",
  "creative_expression",
  "entertainment_release",
  "self_improvement",
  "depth_immersion",
] as const;

export type SynapseAxisKey = (typeof SYNAPSE_AXIS_KEYS)[number];
