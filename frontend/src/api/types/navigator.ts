// 네비게이터(이상향) 백엔드 DTO 타입.

export type IdealType = "OPPOSITE" | "DEEPEN" | "BALANCE" | "CUSTOM";

export type AxisScores8 = Record<string, number>;
export type AxisScores13 = Record<string, number>;

// 성향 6축 / 관심 도메인 — 현재(초상)→목표(이상향) 쌍
export interface DispositionPair {
  key: string;
  label_ko: string;
  current: number;
  target: number;
}
export interface DomainPair {
  domain: string;
  current: number;
  target: number;
}

export interface ProposalItem {
  ideal_type: IdealType;
  scores: AxisScores8; // 폴드용(행동 8축)
  values_temperament: AxisScores13; // 폴드용(가치관·기질 13축)
  disposition: DispositionPair[]; // 성향 현재→목표
  interest: DomainPair[]; // 도메인 현재→목표
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
  target_disposition: Record<string, number> | null;
  target_interest: Record<string, number> | null;
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
  // 주 표시 축: 성향 6축·관심 도메인 현재→목표
  disposition: DispositionPair[];
  interest: DomainPair[];
}

export interface GuideStepItem {
  axis: string;
  label_ko: string;
  kind: "deepen" | "expand";
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
export type PlaylistStatus = "pending" | "ready" | "failed";

export interface PlaylistResponse {
  id: string;
  ideal_id: string;
  title: string;
  summary: string;
  items: PlaylistItemResponse[];
  status: PlaylistStatus;
  youtube_playlist_id: string | null;
  created_at: string;
  updated_at: string;
}
export interface PlaylistSummary {
  id: string;
  title: string;
  item_count: number;
  status: PlaylistStatus;
  youtube_playlist_id: string | null;
  created_at: string;
}

export interface PlaylistChatHandlers {
  onStatus?: (content: string) => void;
  onPlaylist?: (playlist: PlaylistResponse) => void;
}

export interface IdealEvent {
  disposition: Record<string, number>;
  interest: Record<string, number>;
  behavior: AxisScores8;
  values_temperament: AxisScores13;
}

export interface CompleteEvent extends IdealEvent {
  persona_label: string;
  reasoning: string;
  ideal_type: IdealType;
}

export interface ChatStreamHandlers {
  onStatus?: (content: string) => void;
  onIdeal?: (data: IdealEvent) => void;
  onToken?: (content: string) => void;
  onComplete?: (data: CompleteEvent) => void;
}
