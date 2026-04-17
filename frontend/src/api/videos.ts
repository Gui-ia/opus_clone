import { request, toQueryString } from './client';
import type { ProcessVideosResponse, SourceVideoResponse, VideoListParams } from '../types/video';

export const listVideos = (params: VideoListParams = {}) =>
  request<SourceVideoResponse[]>(`/api/videos?${toQueryString(params as Record<string, unknown>)}`);

export const getVideo = (id: string) =>
  request<SourceVideoResponse>(`/api/videos/${id}`);

export const processVideos = (videoIds: string[]) =>
  request<ProcessVideosResponse>('/api/videos/process', {
    method: 'POST',
    body: JSON.stringify({ video_ids: videoIds }),
  });

export const deleteVideos = (videoIds: string[]) =>
  request<{ deleted: string[]; not_found: string[] }>('/api/videos/batch', {
    method: 'DELETE',
    body: JSON.stringify({ video_ids: videoIds }),
  });
