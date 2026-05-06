import { useQuery } from '@tanstack/react-query';
import { fetchDriftStatus, type DriftAlert } from '@/api/observabilityClient';
import { api, type BatchStatus } from '@/services/api';

/**
 * Poll batch status every 3 seconds while batch is processing.
 * Returns the batch status object + convenience booleans.
 */
export function useBatchPolling(batchId: string | null) {
  const query = useQuery<BatchStatus>({
    queryKey: ['batch-status', batchId],
    queryFn: () => api.getBatchStatus(batchId!),
    enabled: !!batchId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 3_000;
    },
  });

  return {
    ...query,
    isProcessing: query.data?.status === 'processing' || query.data?.status === 'queued',
    isComplete: query.data?.status === 'completed',
    isFailed: query.data?.status === 'failed',
    progress: query.data?.progress ?? 0,
  };
}

/**
 * Poll drift status every 30 seconds.
 * Returns alerts array + has-critical flag.
 */
export function useDriftAlerts(enabled = true) {
  const query = useQuery({
    queryKey: ['drift-alerts'],
    queryFn: fetchDriftStatus,
    enabled,
    refetchInterval: 30_000,
  });

  const alerts: DriftAlert[] = query.data?.alerts ?? [];
  const hasCritical = alerts.some(a => a.severity === 'critical' || a.severity === 'high');

  return {
    ...query,
    alerts,
    hasCritical,
    alertCount: alerts.length,
  };
}
