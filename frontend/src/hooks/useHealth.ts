import { useQuery } from '@tanstack/react-query';
import * as api from '../api/health';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 30_000,
  });
}
