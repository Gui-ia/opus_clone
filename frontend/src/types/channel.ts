export type Platform = 'youtube' | 'instagram' | 'tiktok';
export type SourceType = 'feed' | 'stories' | 'reels' | 'shorts' | 'video' | 'live';

export interface ChannelResponse {
  id: string;
  platform: Platform;
  external_id: string;
  username: string;
  display_name: string | null;
  is_active: boolean;
  poll_interval_seconds: number;
  source_types: string[] | null;
  last_polled_at: string | null;
  last_content_at: string | null;
  min_viral_score: number;
  max_clips_per_video: number;
  style_preset: string;
  created_at: string;
  updated_at: string;
}

export interface ChannelCreate {
  platform: Platform;
  external_id: string;
  username: string;
  display_name?: string;
  poll_interval_seconds?: number;
  source_types?: SourceType[];
  preferred_clip_duration_s?: number[];
  min_viral_score?: number;
  max_clips_per_video?: number;
  style_preset?: string;
}

export interface ChannelUpdate {
  display_name?: string | null;
  is_active?: boolean | null;
  poll_interval_seconds?: number | null;
  source_types?: SourceType[] | null;
  min_viral_score?: number | null;
  max_clips_per_video?: number | null;
  style_preset?: string | null;
}

export interface ChannelListParams {
  platform?: Platform;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}
