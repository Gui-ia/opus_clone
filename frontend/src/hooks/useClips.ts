import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/clips';
import type { ClipApproval, ClipListParams } from '../types/clip';
import { toast } from 'sonner';

export function useClips(
  params: ClipListParams = {},
  options?: { refetchInterval?: number },
) {
  return useQuery({
    queryKey: ['clips', params],
    queryFn: () => api.listClips(params),
    staleTime: 15_000,
    refetchInterval: options?.refetchInterval,
  });
}

export function useClip(id: string) {
  return useQuery({
    queryKey: ['clips', id],
    queryFn: () => api.getClip(id),
    enabled: !!id,
  });
}

export function useApproveClip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data?: ClipApproval }) =>
      api.approveClip(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clips'] });
      toast.success('Clip aprovado');
    },
    onError: (err: Error) => {
      toast.error(`Erro ao aprovar clip: ${err.message}`);
    },
  });
}

export function useRejectClip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.rejectClip(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clips'] });
      toast.success('Clip rejeitado');
    },
    onError: (err: Error) => {
      toast.error(`Erro ao rejeitar clip: ${err.message}`);
    },
  });
}
