import { useQuery } from '@tanstack/react-query';
import { checkHealth } from '@/api/ddrClient';

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 30000,
    retry: 1,
  });
}
