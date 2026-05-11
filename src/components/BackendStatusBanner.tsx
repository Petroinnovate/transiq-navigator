import { AlertTriangle, Loader2, CheckCircle2 } from 'lucide-react';
import { useHealthCheck } from '@/hooks/useHealthCheck';

/**
 * Honest connectivity banner for the processing backend (FastAPI at VITE_API_URL).
 * - "unknown": first check in flight — no claim either way.
 * - "critical": /health failed → uploads will not work, surface clearly.
 * - "healthy": small confirmation chip (non-intrusive).
 *
 * No demo/mock data is ever shown. If the backend is offline, the UI is
 * empty + honest, not pretend-populated.
 */
export function BackendStatusBanner({ compact = false }: { compact?: boolean }) {
  const { status } = useHealthCheck();
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';

  if (status === 'healthy') {
    if (compact) return null;
    return (
      <div className="flex items-center gap-2 text-xs text-emerald-400 px-3 py-1.5 rounded-md bg-emerald-500/5 border border-emerald-500/20 w-fit">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Processing backend online
      </div>
    );
  }

  if (status === 'unknown') {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400 px-3 py-1.5 rounded-md bg-slate-500/5 border border-slate-500/20 w-fit">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Checking backend…
      </div>
    );
  }

  return (
    <div
      role="alert"
      className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5 flex-shrink-0" />
        <div className="space-y-1">
          <div className="font-semibold text-amber-200">
            Processing backend is offline
          </div>
          <div className="text-amber-100/80">
            Cannot reach <code className="px-1 rounded bg-black/30">{apiUrl}</code>.
            Uploads, document history, and dashboard generation are disabled until the
            backend is reachable. Authentication still works.
          </div>
        </div>
      </div>
    </div>
  );
}
