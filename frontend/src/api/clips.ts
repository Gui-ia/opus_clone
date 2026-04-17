import { request, toQueryString } from './client';
import type { ClipApproval, ClipListParams, ClipResponse } from '../types/clip';

export const listClips = (params: ClipListParams = {}) =>
  request<ClipResponse[]>(`/api/clips?${toQueryString(params as Record<string, unknown>)}`);

export const getClip = (id: string) =>
  request<ClipResponse>(`/api/clips/${id}`);

export const approveClip = (id: string, data?: ClipApproval) =>
  request<ClipResponse>(`/api/clips/${id}/approve`, {
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });

export const rejectClip = (id: string) =>
  request<ClipResponse>(`/api/clips/${id}/reject`, { method: 'PATCH' });
