import { request, toQueryString } from './client';
import type {
  ChannelCreate,
  ChannelListParams,
  ChannelResponse,
  ChannelUpdate,
} from '../types/channel';
import type { SourceVideoResponse } from '../types/video';

export const listChannels = (params: ChannelListParams = {}) =>
  request<ChannelResponse[]>(`/api/channels?${toQueryString(params as Record<string, unknown>)}`);

export const getChannel = (id: string) =>
  request<ChannelResponse>(`/api/channels/${id}`);

export const createChannel = (data: ChannelCreate) =>
  request<ChannelResponse>('/api/channels', {
    method: 'POST',
    body: JSON.stringify(data),
  });

export const updateChannel = (id: string, data: ChannelUpdate) =>
  request<ChannelResponse>(`/api/channels/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });

export const deleteChannel = (id: string) =>
  request<void>(`/api/channels/${id}`, { method: 'DELETE' });

export const fetchChannelVideos = (channelId: string) =>
  request<SourceVideoResponse[]>(`/api/channels/${channelId}/fetch-videos`, {
    method: 'POST',
  });
