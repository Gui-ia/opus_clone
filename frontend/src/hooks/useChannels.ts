import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/channels';
import type { ChannelCreate, ChannelListParams, ChannelUpdate } from '../types/channel';
import type { SourceVideoResponse } from '../types/video';
import { toast } from 'sonner';

export function useChannels(params: ChannelListParams = {}) {
  return useQuery({
    queryKey: ['channels', params],
    queryFn: () => api.listChannels(params),
    staleTime: 30_000,
  });
}

export function useChannel(id: string) {
  return useQuery({
    queryKey: ['channels', id],
    queryFn: () => api.getChannel(id),
    enabled: !!id,
  });
}

export function useCreateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChannelCreate) => api.createChannel(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Canal criado com sucesso');
    },
    onError: (err: Error) => {
      toast.error(`Erro ao criar canal: ${err.message}`);
    },
  });
}

export function useUpdateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ChannelUpdate }) =>
      api.updateChannel(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Canal atualizado');
    },
    onError: (err: Error) => {
      toast.error(`Erro ao atualizar canal: ${err.message}`);
    },
  });
}

export function useDeleteChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteChannel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['channels'] });
      toast.success('Canal desativado');
    },
    onError: (err: Error) => {
      toast.error(`Erro ao desativar canal: ${err.message}`);
    },
  });
}

export function useFetchChannelVideos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (channelId: string) => api.fetchChannelVideos(channelId),
    onSuccess: (_data, channelId) => {
      qc.invalidateQueries({ queryKey: ['videos'] });
      qc.invalidateQueries({ queryKey: ['channel-videos', channelId] });
      toast.success('Videos buscados com sucesso');
    },
    onError: (err: Error) => {
      toast.error(`Erro ao buscar videos: ${err.message}`);
    },
  });
}
