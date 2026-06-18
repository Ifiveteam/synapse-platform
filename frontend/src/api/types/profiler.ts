export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface TopCategoryItem {
  category_id: string;
  count: number;
}

export interface TopChannelItem {
  channel: string;
  count: number;
}

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
  top_categories: TopCategoryItem[];
  top_channels: TopChannelItem[];
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

export interface HabitMetricsDto {
  channel_concentration: number;
  category_concentration: number;
  category_diversity: number;
  exploration_depth: number;
}

export interface CompareSnapshotSummary {
  snapshot_id: string;
  snapshot_date: string;
  persona_label: string | null;
  summary_text: string;
  scores: Record<string, number>;
  habits: HabitMetricsDto;
  shorts_ratio: number;
  total_videos: number;
}

export interface CompareNarrative {
  headline: string;
  summary_text: string;
  key_shifts: string[];
  stable_traits: string[];
  viewing_pattern_note: string;
}

export interface AnalysisCompareResponse {
  from_snapshot: CompareSnapshotSummary;
  to_snapshot: CompareSnapshotSummary;
  scores_delta: Record<string, number>;
  habits_from: HabitMetricsDto;
  habits_to: HabitMetricsDto;
  habits_delta: HabitMetricsDto;
  shorts_ratio_delta: number;
  traits_added: string[];
  traits_removed: string[];
  channels_added: string[];
  channels_removed: string[];
  narrative: CompareNarrative | null;
  narrative_error: string | null;
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
