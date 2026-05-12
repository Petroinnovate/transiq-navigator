import { AlertTriangle, Loader2, CheckCircle2, Info } from 'lucide-react';
import { useHealthCheck } from '@/hooks/useHealthCheck';

/**
 * Connectivity banner for the app backend.
 *
 * Two backends now power this app:
 *   1. Lovable Cloud (Supabase + edge functions) — handles auth, file uploads,
 *      document processing, dashboard generation, search. ALWAYS used.
 *   2. Legacy FastAPI (VITE_API_URL) — DDR fleet/rig analytics, intelligence,
 *      six-sigma, graph RAG, observability. PENDING migration to Google Cloud.
 *
 * Banner states:
 *   - healthy:        Cloud OK. Tiny chip (or hidden in compact mode).
 *   - healthy + no legacy: Cloud OK + heads-up that DDR/intel features are pending.
 *   - critical:       Cloud unreachable — auth still works but most features won't.
 *   - unknown:        First check in flight.
 */
export function BackendStatusBanner({ compact = false }: { compact?: boolean }) {
  const { status, legacyBackendOnline } = useHealthCheck();

  if (status === 'unknown') {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400 px-3 py-1.5 rounded-md bg-slate-500/5 border border-slate-500/20 w-fit">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Checking backend…
      </div>
    );
  }

  if (status === 'critical') {
    return (
      <div role="alert" className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-1">
            <div className="font-semibold text-amber-200">Lovable Cloud unreachable</div>
            <div className="text-amber-100/80">
              Cannot reach the platform database. Uploads and dashboards are disabled.
            </div>
            <a href="/api-diagnostics" className="inline-block mt-1 text-xs underline text-amber-200 hover:text-amber-100">
              Run diagnostics →
            </a>
          </div>
        </div>
      </div>
    );
  }

  // status === 'healthy'
  if (compact && legacyBackendOnline) return null;

  if (!legacyBackendOnline) {
    return (
      <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 px-4 py-3 text-sm text-cyan-100">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-cyan-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-1">
            <div className="font-semibold text-cyan-200">Lovable Cloud online</div>
            <div className="text-cyan-100/80">
              Upload, processing, dashboard generation, and search are available.
              DDR fleet analytics, intelligence, six-sigma, and graph features are
              pending migration to Google Cloud.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs text-emerald-400 px-3 py-1.5 rounded-md bg-emerald-500/5 border border-emerald-500/20 w-fit">
      <CheckCircle2 className="h-3.5 w-3.5" />
      All backends online
    </div>
  );
}
