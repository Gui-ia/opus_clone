export type ClipStatus =
  | 'planned'
  | 'rendering'
  | 'ready'
  | 'approved'
  | 'rejected'
  | 'publishing'
  | 'published'
  | 'failed';

export const TRANSIENT_CLIP_STATUSES: ClipStatus[] = [
  'rendering',
  'publishing',
];

export interface ClipResponse {
  id: string;
  source_video_id: string;
  start_ms: number;
  end_ms: number;
  hook_text: string | null;
  title_suggestion: string | null;
  hashtags: string[] | null;
  viral_score: number | null;
  confidence: number | null;
  hook_type: string | null;
  category: string | null;
  rationale: string | null;
  minio_key: string | null;
  final_url: string | null;
  thumbnail_url: string | null;
  status: ClipStatus;
  created_at: string;
  rendered_at: string | null;
  approved_at: string | null;
}

export interface ClipApproval {
  title?: string;
  description?: string;
  hashtags?: string[];
  schedule_at?: string;
}

export interface ClipListParams {
  source_video_id?: string;
  status?: ClipStatus;
  page?: number;
  page_size?: number;
}
