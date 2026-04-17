import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/videos';
import type { VideoListParams } from '../types/video';
import { toast } from 'sonner';

export function useVideos(
  params: VideoListParams = {},
  options?: { refetchInterval?: number },
) {
  return useQuery({
    queryKey: ['videos', params],
    queryFn: () => api.listVideos(params),
    staleTime: 15_000,
    refetchInterval: options?.refetchInterval,
  });
}

export function useVideo(id: string) {
  return useQuery({
    queryKey: ['videos', id],
    queryFn: () => api.getVideo(id),
    enabled: !!id,
  });
}

export function useProcessVideos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (videoIds: string[]) => api.processVideos(videoIds),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['videos'] });
      qc.invalidateQueries({ queryKey: ['channel-videos'] });
      toast.success(`${data.queued.length} video(s) enviado(s) para processamento`);
      if (data.skipped.length > 0) {
        toast.info(`${data.skipped.length} video(s) ignorado(s) (ja processados ou nao encontrados)`);
      }
    },
    onError: (err: Error) => {
      toast.error(`Erro ao processar videos: ${err.message}`);
    },
  });
}

export function useDeleteVideos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (videoIds: string[]) => api.deleteVideos(videoIds),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['videos'] });
      qc.invalidateQueries({ queryKey: ['channel-videos'] });
      toast.success(`${data.deleted.length} video(s) excluido(s)`);
    },
    onError: (err: Error) => {
      toast.error(`Erro ao excluir videos: ${err.message}`);
    },
  });
}
