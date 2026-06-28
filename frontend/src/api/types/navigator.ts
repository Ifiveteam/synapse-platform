// 네비게이터(이상향) 백엔드 DTO 타입.

export type IdealType = "OPPOSITE" | "DEEPEN" | "BALANCE" | "CUSTOM";

export type AxisScores8 = Record<string, number>;
export type AxisScores13 = Record<string, number>;

export interface ProposalItem {
  ideal_type: IdealType;
  scores: AxisScores8;
  values_temperament: AxisScores13;
  persona_label: string;
  reasoning: string;
}
export interface ProposalsResponse {
  proposals: ProposalItem[];
}

export interface IdealResponse {
  id: string;
  ideal_type: IdealType;
  scores: AxisScores8;
  values_temperament: AxisScores13 | null;
  persona_label: string;
  reasoning: string;
  is_active: boolean;
  updated_at: string;
}

export interface AxisGapItem {
  axis: string;
  label_ko: string;
  current: number;
  ideal: number;
  gap: number;
}
export interface ComparisonResponse {
  current: AxisScores8;
  ideal: AxisScores8;
  gaps: AxisGapItem[];
  total_gap: number;
  current_vt: AxisScores13 | null;
  ideal_vt: AxisScores13 | null;
}

export interface GuideStepItem {
  axis: string;
  label_ko: string;
  title: string;
  detail: string;
  priority: number;
}
export interface GuideResponse {
  summary: string;
  steps: GuideStepItem[];
  generated_at: string | null;
  stale: boolean;
}

export interface PlaylistItemResponse {
  video_id: string;
  title: string;
  channel: string;
  channel_id: string;
  thumbnail_url: string;
  url: string;
  reason: string;
}
export interface PlaylistResponse {
  id: string;
  ideal_id: string;
  title: string;
  summary: string;
  items: PlaylistItemResponse[];
  youtube_playlist_id: string | null;
  created_at: string;
  updated_at: string;
}
export interface PlaylistSummary {
  id: string;
  title: string;
  item_count: number;
  youtube_playlist_id: string | null;
  created_at: string;
}

export interface PlaylistChatHandlers {
  onStatus?: (content: string) => void;
  onPlaylist?: (playlist: PlaylistResponse) => void;
}

export interface IdealEvent {
  behavior: AxisScores8;
  values_temperament: AxisScores13;
}

export interface ChatStreamHandlers {
  onStatus?: (content: string) => void;
  onIdeal?: (data: IdealEvent) => void;
  onToken?: (content: string) => void;
}
