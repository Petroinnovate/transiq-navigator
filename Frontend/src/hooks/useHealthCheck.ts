import { useQuery } from '@tanstack/react-query';
import axios from '@/lib/axios';

type HealthStatus = 'healthy' | 'critical' | 'unknown';

interface HealthCheckResult {
  status: HealthStatus;
  isHealthy: boolean;
  isCritical: boolean;
}

async function fetchHealth(): Promise<HealthStatus> {
  try {
    const { data } = await axios.get('/health');
    return data?.status === 'ok' || data?.status === 'healthy' ? 'healthy' : 'critical';
  } catch {
    return 'critical';
  }
}

export function useHealthCheck(): HealthCheckResult {
  const { data: status = 'unknown' } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    staleTime: 25_000,
    retry: 1,
  });

  return {
    status,
    isHealthy: status === 'healthy',
    isCritical: status === 'critical',
  };
}
