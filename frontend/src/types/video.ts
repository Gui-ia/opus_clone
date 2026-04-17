export type VideoStatus =
  | 'discovered'
  | 'downloading'
  | 'downloaded'
  | 'transcribing'
  | 'analyzing'
  | 'scoring'
  | 'ready_to_clip'
  | 'clipping'
  | 'completed'
  | 'failed'
  | 'skipped';

export const VIDEO_STATUS_ORDER: VideoStatus[] = [
  'discovered',
  'downloading',
  'downloaded',
  'transcribing',
  'analyzing',
  'scoring',
  'ready_to_clip',
  'clipping',
  'completed',
];

export const TRANSIENT_VIDEO_STATUSES: VideoStatus[] = [
  'downloading',
  'transcribing',
  'analyzing',
  'scoring',
  'clipping',
];

export interface SourceVideoResponse {
  id: string;
  channel_id: string;
  external_id: string;
  source_type: string;
  url: string;
  title: string | null;
  published_at: string | null;
  duration_s: number | null;
  view_count: number | null;
  status: VideoStatus;
  error_message: string | null;
  retry_count: number;
  discovered_at: string;
  completed_at: string | null;
}

export interface VideoListParams {
  channel_id?: string;
  status?: VideoStatus;
  page?: number;
  page_size?: number;
}

export interface ProcessVideosResponse {
  queued: string[];
  skipped: string[];
}
